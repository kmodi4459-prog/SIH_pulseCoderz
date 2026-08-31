// notifications.js — Email alerts via Nodemailer

const nodemailer = require('nodemailer');

const transporter = nodemailer.createTransport({
  service: 'gmail',
  auth: {
    user: process.env.EMAIL_USER,
    pass: process.env.EMAIL_PASS
  }
});

async function sendAlertEmail(officialEmail, alertData) {
  const { victimId, riskLevel, score, trend } = alertData;

  const mailOptions = {
    from: process.env.EMAIL_USER,
    to: officialEmail,
    subject: `[${riskLevel.toUpperCase()} ALERT] Victim ${victimId} needs attention`,
    html: `
      <h3>Distress Alert Triggered</h3>
      <p><strong>Victim ID:</strong> ${victimId}</p>
      <p><strong>Risk Level:</strong> ${riskLevel}</p>
      <p><strong>Current Distress Score:</strong> ${score}/100</p>
      <p><strong>Trend:</strong> ${trend}</p>
      <p>Please review this case in the dashboard and take appropriate action.</p>
    `
  };

  try {
    await transporter.sendMail(mailOptions);
    console.log(`Alert email sent to ${officialEmail} for ${victimId} (${riskLevel})`);
    return true;
  } catch (err) {
    console.error('Email send failed:', err.message);
    return false; // Don't crash the server if email fails
  }
}

module.exports = { sendAlertEmail };