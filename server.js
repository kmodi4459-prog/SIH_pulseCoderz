const express = require("express");
const cors = require("cors");
const bcrypt = require("bcrypt");
const { connectDB } = require("./db");
const { Victim, Interaction, DistressScore, Alert } = require("./models");
const { PriorityQueue, checkThresholdAndTrend, THRESHOLDS } = require("./priorityQueue");

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());          // allow frontend (different port) to call this API
app.use(express.json());

const casePriorityQueue = new PriorityQueue();
connectDB();


const asyncHandler = (fn) => (req, res, next) => fn(req, res, next).catch(next);

// 1. HOME + TEST
app.get("/", (req, res) => {
  res.send("Mental Health Monitoring Server is Running");
});

app.get("/test", (req, res) => {
  res.json({ success: true, message: "API is working" });
});

// 2. VICTIM REGISTRATION (PII hashed, saved to DB)
app.post("/victim", asyncHandler(async (req, res) => {
  const { victimId, name, contact, caseType, district, state, registeredVia } = req.body;
  if (!victimId || !name || !district) {
    return res.status(400).json({
      success: false,
      message: "victimId, name, and district are required fields"
    });
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
}));

// GET a single victim's basic profile (no PII returned — just non-sensitive fields)
app.get("/victim/:victimId", asyncHandler(async (req, res) => {
  const victim = await Victim.findOne({ victimId: req.params.victimId });
  if (!victim) return res.status(404).json({ success: false, message: "Victim not found" });

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
}));

// 3. DISTRESS SCORE — save, check threshold, auto-alert, update priority queue

app.post("/distress-score", asyncHandler(async (req, res) => {
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
    await Alert.create({
      victimId, triggeredScore: result.latestScore, riskLevel: result.riskLevel, status: "open"
    });

    if (casePriorityQueue.heap.some(item => item.victimId === victimId)) {
      casePriorityQueue.updateScore(victimId, result.latestScore);
    } else {
      casePriorityQueue.insert({ victimId, score: result.latestScore, riskLevel: result.riskLevel });
    }
    alertCreated = true;
  }

  res.json({
    success: true, victimId,
    distressScore: result.latestScore,
    riskLevel: result.riskLevel || "LOW",
    trend: result.trend,
    alertCreated
  });
}));

// GET full score history for one victim — this is what the dashboard's trend
// line chart needs (not just the latest score)
app.get("/distress-score/:victimId", asyncHandler(async (req, res) => {
  const history = await DistressScore.find({ victimId: req.params.victimId })
    .sort({ calculatedAt: 1 })
    .select("score contributingFactors calculatedAt -_id");

  res.json({ success: true, victimId: req.params.victimId, history });
}));

// 4. ALERTS — list + acknowledge/resolve


app.get("/alerts", asyncHandler(async (req, res) => {
  const { status, riskLevel } = req.query;
  const filter = {};
  if (status) filter.status = status;
  if (riskLevel) filter.riskLevel = riskLevel;

  const alerts = await Alert.find(filter).sort({ createdAt: -1 });
  res.json({ success: true, count: alerts.length, alerts });
}));

// Counsellor/official marks an alert as acknowledged or resolved
app.patch("/alerts/:alertId", asyncHandler(async (req, res) => {
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
}));

// 5. PRIORITY CASES — for the dashboard's "most urgent" list
app.get("/priority-cases", (req, res) => {
  const n = parseInt(req.query.n) || 5;
  res.json({ success: true, topCases: casePriorityQueue.getTopN(n) });
});

// CENTRALIZED ERROR HANDLER — catches anything thrown in asyncHandler routes
// so the server never crashes on an unexpected error

app.use((err, req, res, next) => {
  console.error("Unhandled error:", err.message);
  res.status(500).json({ success: false, message: "Something went wrong on the server" });
});

// SERVER START
app.listen(PORT, () => {
  console.log(`Server running at http://localhost:${PORT}`);
  console.log(`Alert thresholds -> amber: ${THRESHOLDS.amber}, red: ${THRESHOLDS.red}`);
});