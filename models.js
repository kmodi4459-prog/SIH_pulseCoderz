const mongoose = require("mongoose");

const victimSchema = new mongoose.Schema({
  victimId: { type: String, required: true, unique: true },
  nameHash: { type: String, required: true },
  contactHash: { type: String },
  caseType: { type: String, default: "witness_intimidation" },
  registeredVia: { type: String, default: "Chatbot" },
  district: { type: String, required: true },
  state: { type: String, default: "Unknown" },
  createdAt: { type: Date, default: Date.now }
});

const interactionSchema = new mongoose.Schema({
  victimId: { type: String, required: true },
  channel: { type: String, enum: ["chat", "voice", "kiosk"], default: "chat" },
  sentimentScore: { type: Number },
  voiceStress: { type: Number },
  createdAt: { type: Date, default: Date.now }
});

const distressScoreSchema = new mongoose.Schema({
  victimId: { type: String, required: true },
  score: { type: Number, required: true },
  contributingFactors: [{ type: String }],
  calculatedAt: { type: Date, default: Date.now }
});

const alertSchema = new mongoose.Schema({
  victimId: { type: String, required: true },
  triggeredScore: { type: Number, required: true },
  riskLevel: { type: String, enum: ["LOW", "MEDIUM", "HIGH"], required: true },
  status: { type: String, enum: ["open", "acknowledged", "resolved"], default: "open" },
  assignedOfficialId: { type: String },
  createdAt: { type: Date, default: Date.now }
});

module.exports = {
  Victim: mongoose.model("Victim", victimSchema),
  Interaction: mongoose.model("Interaction", interactionSchema),
  DistressScore: mongoose.model("DistressScore", distressScoreSchema),
  Alert: mongoose.model("Alert", alertSchema)
};