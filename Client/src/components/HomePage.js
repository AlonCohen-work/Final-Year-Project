import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import "../styles/HomePage.css";

import weekleyScu from "../images/weekleyScu.png";
import ManageHours from "../images/ManageHours.png";
import Employee_Request from "../images/iconapp-Photo.png";

const HomePage = () => {
  const [user, setUser] = useState(null);
  const [warning, setWarning] = useState([]);
  const navigate = useNavigate();

 useEffect(() => {
  const savedUser = JSON.parse(localStorage.getItem("user"));
  console.log("📥 Fetched user from localStorage:", savedUser);
  if (!savedUser) return;

  setUser(savedUser);
  
  if (!savedUser.Workplace) {
    console.log("❌ No workplace found for user.");
    return;
  }

  console.log(`🏨 Fetching latest schedule for hotel: ${savedUser.Workplace}`);
  fetch(`/get-latest-result/${savedUser.Workplace}`)
    .then(res => res.json())
    .then(data => {
      console.log("📦 Received schedule data:", data);

      if (data.status !== "partial" || !data.notes) {
        console.log("✅ Schedule is full or no issues found.");
        return;
      }

      const issues = Array.isArray(data.notes) ? data.notes : [];
      console.log("⚠️ Found problematic shifts:", issues);

      // מנהל רואה הכל
      if (savedUser.job === "management") {
        console.log("🧑‍💼 User is management — showing all warnings.");
        setWarning(issues.map(i => `${i.shift} - ${i.position}`));
        return;
      }

      // אחמש רואה הכל
      if (savedUser.ShiftManager === true) {
        console.log("👮 User is Shift Manager — showing all warnings.");
        setWarning(issues.map(i => `${i.shift} - ${i.position}`));
        return;
      }

      // בדיקה אם יש issue שדורש נשק והמשתמש מאושר
      const foundWeaponIssue = issues.some(i => i.weapon === true);
      const isSUP = issues.some(i => i.position === "Shift Supervisor");
      if (foundWeaponIssue && savedUser.WeaponCertified === true && isSUP===false) {
        console.log("🔫 User has Weapon Certification — showing weapon warnings.");
        setWarning(issues.filter(i => i.weapon === true).map(i => `${i.shift} - ${i.position}`));
        return;
      }

      // בדיקה אם יש issue שלא דורש נשק והמשתמש לא מוסמך
      const foundNonWeaponIssue = issues.some(i => i.weapon === false);
      if (foundNonWeaponIssue && savedUser.WeaponCertified === false  && isSUP===false) {
        console.log("✅ User without weapon cert — showing non-weapon warnings.");
        setWarning(issues.filter(i => i.weapon === false).map(i => `${i.shift} - ${i.position}`));
        return;
      }

      console.log("ℹ️ No relevant issues to show.");
    })
    .catch(err => console.error("❌ Failed to fetch schedule result:", err));
}, []);



  const handleCellClick = (path) => {
    navigate(path);
  };

  return (
    <div className="homepage">
      <h1>Welcome, {user ? user.name : "Guest"}!</h1>

      {warning.length > 0 && (
        <div className="warning-banner">
          {user?.job === "management"
            ? `Partial schedule detected. Problematic shifts: ${warning.join(", ")}. Please inform employees to update their availability.`
            : `Partial schedule: please resubmit your availability. Problematic shifts: ${warning.join(", ")}`}
        </div>
      )}

      <div className="table-container">
        <table className="custom-table">
          <tbody>
            <tr>
              <td onClick={() => handleCellClick('/weekleyScu')}>
                <img src={weekleyScu} alt="Weekly Schedule" />
              </td>
            </tr>

            {user?.job === 'Employee' && (
              <tr>
                <td onClick={() => handleCellClick('/EmployeeRequest')}>
                  <img src={Employee_Request} alt="Employee Request" />
                </td>
              </tr>
            )}

            {user?.job === 'management' && (
              <tr>
                <td onClick={() => handleCellClick('/manage-hours')}>
                  <img src={ManageHours} alt="Manage Hours" />
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default HomePage;
