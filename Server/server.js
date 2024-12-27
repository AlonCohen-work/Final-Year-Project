const express = require("express");
const mongojs = require("mongojs");
const cors = require("cors");
const app = express();

app.use(express.json());
app.use(cors());

// חיבור למסד הנתונים
const db = mongojs("mongodb://localhost:27017/people");
const people_coll = db.collection("people");

db.on("connect", () => {
  console.log("Connected to MongoDB");
});

db.on("error", (err) => {
  console.error("Database connection error:", err);
});

// נתיב התחברות
app.post("/login", (req, res) => {
  const { id, password } = req.body;

  console.log("📩 Received login request:", req.body);

  // הבטחת המרה ל-Number לטיפוס Int32
  const numericId = parseInt(id);

  if (isNaN(numericId)) {
    return res.status(400).send("Invalid ID format");
  }

  people_coll.findOne({ _id: numericId }, (err, user) => {
    if (err) {
      console.error("❌ Database error:", err);
      return res.status(500).send("שגיאה במסד הנתונים");
    }

    if (user) {
      if (user.password === password) {
        console.log(`✅ Login successful for user: ${id}`);
        res.json({
          success: true,
          id: user._id,
          job: user.job,
        });
      } else {
        console.log(`❌ Incorrect password for user: ${id}`);
        res.json({ success: false, message: "מספר זיהוי או סיסמה לא נכונים" });
      }
    } else {
      console.log(`❌ User not found: ${id}`);
      res.json({ success: false, message: "מספר זיהוי או סיסמה לא נכונים" });
    }
  });
});

// הפעלת השרת
const PORT = process.env.PORT || 3002;
app.listen(PORT, () => {
  console.log(`🚀 Server running on port ${PORT}`);
});
