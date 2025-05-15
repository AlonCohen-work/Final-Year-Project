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

  // מפרק את שדה ה-shift ליום ומשמרת
  const parseShift = (shiftStr) => {
    const parts = shiftStr.split(" ");
    return {
      day: parts[0] || "",
      shift: parts[1] || "",
    };
  };

  // פונקציה שבודקת אם היום רלוונטי למשתמש
  const isIssueRelevantForUser = (issueDay, userSelectedDays) => {
    return !userSelectedDays.some(
      (d) => d.day.toLowerCase() === issueDay.toLowerCase()
    );
  };

  useEffect(() => {
    const savedUser = JSON.parse(localStorage.getItem("user"));
    if (!savedUser) return;

    setUser(savedUser);

    if (!savedUser.Workplace) return;

    const selectedDays = savedUser.selectedDays || [];

    fetch(`/get-latest-result/${savedUser.Workplace}`)
      .then((res) => res.json())
      .then((data) => {
        if (data.status !== "partial" || !data.notes) return;

        const issues = Array.isArray(data.notes) ? data.notes : [];

        if (savedUser.job === "management") {
          setWarning(issues);
          return;
        }

        if (savedUser.ShiftManager === true) {
          const filtered = issues.filter((i) => {
            const { day } = parseShift(i.shift);
            return isIssueRelevantForUser(day, selectedDays);
          });
          setWarning(filtered);
          return;
        }

        const foundWeaponIssue = issues.some((i) => i.weapon === true);
        const foundNonWeaponIssue = issues.some((i) => i.weapon === false);
        const isSUP = issues.some((i) => i.position === "Shift Supervisor");

        if (foundWeaponIssue && savedUser.WeaponCertified && !isSUP) {
          const filtered = issues.filter((i) => {
            const { day } = parseShift(i.shift);
            return i.weapon === true && isIssueRelevantForUser(day, selectedDays);
          });
          setWarning(filtered);
          return;
        }

        if (foundNonWeaponIssue && !savedUser.WeaponCertified && !isSUP) {
          const filtered = issues.filter((i) => {
            const { day } = parseShift(i.shift);
            return (
              i.weapon === false && isIssueRelevantForUser(day, selectedDays)
            );
          });
          setWarning(filtered);
          return;
        }
      })
      .catch((err) =>
        console.error("❌ Failed to fetch schedule result:", err)
      );
  }, []);

  const handleCellClick = (path) => {
    navigate(path);
  };

  return (
    <div className="homepage">
      <h1>Welcome, {user ? user.name : "Guest"}!</h1>

      {warning.length > 0 && (
        <div className="warning-banner">
          <strong>
            <span role="img" aria-label="Warning">
              ⚠️
            </span>{" "}
            Partial schedule detected — {warning.length} problematic shifts:
          </strong>
          <ul>
            {warning.map((i, idx) => {
              const { day, shift } = parseShift(i.shift);
              return (
                <li key={idx}>
                  {day} — {shift} — {i.position}
                </li>
              );
            })}
          </ul>
          <p>Please submit your updated availability.</p>
        </div>
      )}

      <div className="table-container">
        <table className="custom-table">
          <tbody>
            <tr>
              <td onClick={() => handleCellClick("/weekleyScu")}>
                <img src={weekleyScu} alt="Weekly Schedule" />
              </td>
            </tr>

            {user?.job === "Employee" && (
              <tr>
                <td onClick={() => handleCellClick("/EmployeeRequest")}>
                  <img src={Employee_Request} alt="Employee Request" />
                </td>
              </tr>
            )}

            {user?.job === "management" && (
              <tr>
                <td onClick={() => handleCellClick("/manage-hours")}>
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
