const express = require("express");
const http = require("http");
const { Server } = require("socket.io");
const cors = require("cors");
const bcrypt = require("bcrypt");
const { connectDB } = require("./db");
const { Victim, Interaction, DistressScore, Alert, Official, AccessLog } = require("./models");
const { PriorityQueue, checkThresholdAndTrend, THRESHOLDS } = require("./priorityQueue");

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(express.json());

// Wrap the Express app in a plain HTTP server so Socket.io can attach to it
const httpServer = http.createServer(app);
const io = new Server(httpServer, {
  cors: { origin: "*" } // for hackathon demo; restrict this to your frontend's URL in production
});

io.on("connection", (socket) => {
  console.log("Dashboard connected:", socket.id);
  socket.on("disconnect", () => console.log("Dashboard disconnected:", socket.id));
});

const casePriorityQueue = new PriorityQueue();
connectDB();

// 1. HOME + TEST
app.get("/", (req, res) => {
  res.send("Mental Health Monitoring Server is Running");
});

app.get("/test", (req, res) => {
  res.json({ success: true, message: "API is working" });
});

// 2. OFFICIAL REGISTRATION + LOGIN (role-based access)
app.post("/official/register", async (req, res) => {
  try {
    const { officialId, name, role, district, state, password } = req.body;
    if (!officialId || !name || !role || !password) {
      return res.status(400).json({ success: false, message: "officialId, name, role, and password are required" });
    }

    const passwordHash = await bcrypt.hash(password, 10);
    const official = await Official.create({ officialId, name, role, district, state, passwordHash });

    res.status(201).json({
      success: true,
      message: "Official registered",
      official: { officialId: official.officialId, name: official.name, role: official.role }
    });
  } catch (err) {
    res.status(500).json({ success: false, message: err.message });
  }
});

app.post("/official/login", async (req, res) => {
  try {
    const { officialId, password } = req.body;
    if (!officialId || !password) {
      return res.status(400).json({ success: false, message: "officialId and password are required" });
    }

    const official = await Official.findOne({ officialId });
    if (!official) {
      return res.status(401).json({ success: false, message: "Invalid officialId or password" });
    }

    const isMatch = await bcrypt.compare(password, official.passwordHash);
    if (!isMatch) {
      return res.status(401).json({ success: false, message: "Invalid officialId or password" });
    }

    // Note: for the hackathon prototype we return the official's role/scope
    // directly. In a production system this would be a signed JWT instead.
    res.json({
      success: true,
      message: "Login successful",
      official: {
        officialId: official.officialId,
        name: official.name,
        role: official.role,       // counsellor / district_official / state_official / national_official
        district: official.district,
        state: official.state
      }
    });
  } catch (err) {
    res.status(500).json({ success: false, message: err.message });
  }
});

// 3. VICTIM REGISTRATION (PII hashed, saved to DB)
app.post("/victim", async (req, res) => {
  try {
    const { victimId, name, contact, caseType, district, state, registeredVia } = req.body;
    if (!victimId || !name || !district) {
      return res.status(400).json({ success: false, message: "victimId, name, and district are required fields" });
    }

    const nameHash = await bcrypt.hash(name, 10);
    const contactHash = contact ? await bcrypt.hash(contact, 10) : undefined;

    const victim = await Victim.create({
      victimId, nameHash, contactHash,
      caseType: caseType || "witness_intimidation",
      registeredVia: registeredVia || "Chatbot",
      district, state: state || "Unknown"
    });

    res.status(201).json({
      success: true,
      message: "Victim registered (PII stored as hash)",
      victim: { victimId: victim.victimId, district: victim.district }
    });
  } catch (err) {
    res.status(500).json({ success: false, message: err.message });
  }
});

// GET a victim profile — requires officialId in query so we can log who accessed it
app.get("/victim/:victimId", async (req, res) => {
  try {
    const victim = await Victim.findOne({ victimId: req.params.victimId });
    if (!victim) return res.status(404).json({ success: false, message: "Victim not found" });

    const { officialId } = req.query;
    if (officialId) {
      await AccessLog.create({
        officialId,
        victimId: req.params.victimId,
        action: "view_profile"
      });
    }

    res.json({
      success: true,
      victim: {
        victimId: victim.victimId,
        caseType: victim.caseType,
        district: victim.district,
        state: victim.state,
        registeredVia: victim.registeredVia,
        createdAt: victim.createdAt
      }
    });
  } catch (err) {
    res.status(500).json({ success: false, message: err.message });
  }
});

// 4. DISTRESS SCORE — save, check threshold, auto-alert, update priority queue
app.post("/distress-score", async (req, res) => {
  try {
    const { victimId, score, contributingFactors } = req.body;

    if (!victimId || score === undefined || score === null) {
      return res.status(400).json({ success: false, message: "victimId and score are required" });
    }
    if (typeof score !== "number" || score < 0 || score > 100) {
      return res.status(400).json({ success: false, message: "score must be a number between 0 and 100" });
    }

    await DistressScore.create({ victimId, score, contributingFactors: contributingFactors || [] });

    const history = await DistressScore.find({ victimId }).sort({ calculatedAt: 1 });
    const result = checkThresholdAndTrend(history.map(h => h.score));

    let alertCreated = false;
    if (result.shouldAlert) {
      const newAlert = await Alert.create({
        victimId, triggeredScore: result.latestScore, riskLevel: result.riskLevel, status: "open"
      });

      if (casePriorityQueue.heap.some(item => item.victimId === victimId)) {
        casePriorityQueue.updateScore(victimId, result.latestScore);
      } else {
        casePriorityQueue.insert({ victimId, score: result.latestScore, riskLevel: result.riskLevel });
      }
      alertCreated = true;

      // Push this alert to every connected dashboard instantly
      io.emit("newAlert", {
        alertId: newAlert._id,
        victimId,
        riskLevel: result.riskLevel,
        score: result.latestScore,
        trend: result.trend,
        createdAt: newAlert.createdAt
      });
    }

    res.json({
      success: true, victimId,
      distressScore: result.latestScore,
      riskLevel: result.riskLevel || "LOW",
      trend: result.trend,
      alertCreated
    });
  } catch (err) {
    res.status(500).json({ success: false, message: err.message });
  }
});

// GET full score history — logs access if officialId is passed
app.get("/distress-score/:victimId", async (req, res) => {
  try {
    const history = await DistressScore.find({ victimId: req.params.victimId })
      .sort({ calculatedAt: 1 })
      .select("score contributingFactors calculatedAt -_id");

    const { officialId } = req.query;
    if (officialId) {
      await AccessLog.create({
        officialId,
        victimId: req.params.victimId,
        action: "view_score_history"
      });
    }

    res.json({ success: true, victimId: req.params.victimId, history });
  } catch (err) {
    res.status(500).json({ success: false, message: err.message });
  }
});

// 5. ALERTS — list + acknowledge/resolve
app.get("/alerts", async (req, res) => {
  try {
    const { status, riskLevel, officialId } = req.query;
    const filter = {};
    if (status) filter.status = status;
    if (riskLevel) filter.riskLevel = riskLevel;

    const alerts = await Alert.find(filter).sort({ createdAt: -1 });

    if (officialId) {
      // log once per bulk view rather than per-alert
      for (const alert of alerts) {
        await AccessLog.create({ officialId, victimId: alert.victimId, action: "view_alert" });
      }
    }

    res.json({ success: true, count: alerts.length, alerts });
  } catch (err) {
    res.status(500).json({ success: false, message: err.message });
  }
});

app.patch("/alerts/:alertId", async (req, res) => {
  try {
    const { status, assignedOfficialId } = req.body;
    const validStatuses = ["open", "acknowledged", "resolved"];
    if (status && !validStatuses.includes(status)) {
      return res.status(400).json({ success: false, message: `status must be one of ${validStatuses.join(", ")}` });
    }

    const alert = await Alert.findByIdAndUpdate(
      req.params.alertId,
      { ...(status && { status }), ...(assignedOfficialId && { assignedOfficialId }) },
      { new: true }
    );
    if (!alert) return res.status(404).json({ success: false, message: "Alert not found" });

    res.json({ success: true, alert });
  } catch (err) {
    res.status(500).json({ success: false, message: err.message });
  }
});

// 6. PRIORITY CASES
app.get("/priority-cases", (req, res) => {
  const n = parseInt(req.query.n) || 5;
  res.json({ success: true, topCases: casePriorityQueue.getTopN(n) });
});

// 7. ACCESS LOG — see who viewed what (transparency/audit trail)
app.get("/access-logs", async (req, res) => {
  try {
    const { victimId, officialId } = req.query;
    const filter = {};
    if (victimId) filter.victimId = victimId;
    if (officialId) filter.officialId = officialId;

    const logs = await AccessLog.find(filter).sort({ timestamp: -1 }).limit(100);
    res.json({ success: true, count: logs.length, logs });
  } catch (err) {
    res.status(500).json({ success: false, message: err.message });
  }
});

// SERVER START
httpServer.listen(PORT, () => {
  console.log(`Server running at http://localhost:${PORT}`);
  console.log(`Socket.io ready for real-time alerts`);
  console.log(`Alert thresholds -> amber: ${THRESHOLDS.amber}, red: ${THRESHOLDS.red}`);
});