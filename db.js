const mongoose = require("mongoose");

const connectDB = async () => {
  try {
    const conn = await mongoose.connect(process.env.MONGO_URI || "mongodb://127.0.0.1:27017/distress_db", {
      serverSelectionTimeoutMS: 2000 // 2 second mein timeout
    });
    console.log(`MongoDB Connected: ${conn.connection.host}`);
  } catch (error) {
    console.warn("⚠️ MongoDB connection failed. Running server without database persistence.");
  }
};

module.exports = { connectDB };