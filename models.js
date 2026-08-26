// models.js
// Database schema for the AI Mental Health Monitoring System (PS94)
// Run: npm install mongoose bcrypt

const mongoose = require('mongoose');
const bcrypt = require('bcrypt');

// ---------- 1. VICTIM ----------
// PII fields (name, contact) are hashed to demonstrate privacy protection.
// In a real system you'd use proper encryption + access control, but for a
// hackathon prototype, hashing + an access log is enough to show the concept.
const victimSchema = new mongoose.Schema({
  victimId: { type: String, required: true, unique: true }, // e.g. "V-1001"
  nameHash: { type: String, required: true },   // bcrypt hash, never store plain name
  contactHash: { type: String, required: true },
  caseType: {
    type: String,
    enum: ['rape_gang_rape', 'murder_grievous_hurt', 'arson', 'witness_intimidation', 'caste_violence'],
    required: true
  },
  registeredVia: {
    type: String,
    enum: ['NHAA', 'Portal', 'Chatbot', 'MobileApp', 'IVRS'],
    default: 'Chatbot'
  },
  district: { type: String, required: true },
  state: { type: String, required: true },
  createdAt: { type: Date, default: Date.now }
});

// Helper to hash PII before saving (call this when creating a victim)
victimSchema.statics.hashPII = async function (plainText) {
  const saltRounds = 10;
  return bcrypt.hash(plainText, saltRounds);
};

// ---------- 2. INTERACTION ----------
// Every chatbot/IVRS/SMS message exchange gets logged here
const interactionSchema = new mongoose.Schema({
  victimId: { type: String, required: true, ref: 'Victim' },
  channel: { type: String, enum: ['Chatbot', 'IVRS', 'SMS', 'WebPortal'], default: 'Chatbot' },
  messageText: { type: String, required: true }, // raw text (or transcribed voice)
  sentimentLabel: { type: String },   // filled by the NLP module: e.g. "fear", "hopelessness"
  sentimentScore: { type: Number },   // -1 to 1, filled by the NLP module
  responseTimeSeconds: { type: Number }, // how long victim took to reply — engagement signal
  timestamp: { type: Date, default: Date.now }
});

// ---------- 3. DISTRESS SCORE ----------
// One record per scoring event — this is what powers the trend line
const distressScoreSchema = new mongoose.Schema({
  victimId: { type: String, required: true, ref: 'Victim' },
  score: { type: Number, required: true, min: 0, max: 100 },
  contributingFactors: [{ type: String }], // e.g. ["negative sentiment in last 3 messages", "reduced engagement"]
  calculatedAt: { type: Date, default: Date.now }
});

// ---------- 4. ALERT ----------
const alertSchema = new mongoose.Schema({
  victimId: { type: String, required: true, ref: 'Victim' },
  triggeredScore: { type: Number, required: true },
  riskLevel: { type: String, enum: ['amber', 'red'], required: true }, // amber = medium, red = high
  status: { type: String, enum: ['open', 'acknowledged', 'resolved'], default: 'open' },
  assignedOfficialId: { type: String, ref: 'Official' },
  createdAt: { type: Date, default: Date.now }
});

// ---------- 5. INTERVENTION ----------
const interventionSchema = new mongoose.Schema({
  victimId: { type: String, required: true, ref: 'Victim' },
  alertId: { type: mongoose.Schema.Types.ObjectId, ref: 'Alert' },
  type: {
    type: String,
    enum: ['counselling', 'medical', 'witness_protection', 'relocation', 'financial_aid', 'legal_aid'],
    required: true
  },
  notes: { type: String },
  performedBy: { type: String, ref: 'Official' },
  performedAt: { type: Date, default: Date.now }
});

// ---------- 6. OFFICIAL ----------
// Counsellors, district/state/national officials — role-based access
const officialSchema = new mongoose.Schema({
  officialId: { type: String, required: true, unique: true },
  name: { type: String, required: true }, // officials aren't PII-sensitive like victims, ok to store plain
  role: { type: String, enum: ['counsellor', 'district_official', 'state_official', 'national_official'], required: true },
  district: { type: String },
  state: { type: String },
  passwordHash: { type: String, required: true } // for login, always store hashed
});

// ---------- ACCESS LOG (extra credit for the "security" part of the PS) ----------
const accessLogSchema = new mongoose.Schema({
  officialId: { type: String, required: true },
  victimId: { type: String, required: true },
  action: { type: String, enum: ['view_profile', 'view_score_history', 'view_alert'], required: true },
  timestamp: { type: Date, default: Date.now }
});

module.exports = {
  Victim: mongoose.model('Victim', victimSchema),
  Interaction: mongoose.model('Interaction', interactionSchema),
  DistressScore: mongoose.model('DistressScore', distressScoreSchema),
  Alert: mongoose.model('Alert', alertSchema),
  Intervention: mongoose.model('Intervention', interventionSchema),
  Official: mongoose.model('Official', officialSchema),
  AccessLog: mongoose.model('AccessLog', accessLogSchema)
};