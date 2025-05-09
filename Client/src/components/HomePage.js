import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import "../styles/HomePage.css";

// שמות קבצי תמונה
import weekleyScu from "../images/weekleyScu.png";
import ManageHours from "../images/ManageHours.png";
import Employee_Request from "../images/iconapp-Photo.png";

const HomePage = () => {
  const [user, setUser] = useState(null);
  const [warning, setWarning] = useState([]);
  const navigate = useNavigate();

  useEffect(() => {
    const savedUser = JSON.parse(localStorage.getItem("user"));
    if (savedUser) {
      setUser(savedUser);

      if (savedUser.Workplace) {
        // שליפת תוצאה אחרונה ממונגו
        fetch(`/get-latest-result/${savedUser.Workplace}`)
          .then(res => res.json())
          .then(data => {
            if (data.status === "partial") {
              setWarning(data.notes ? data.notes.split(", ") : []);
            }
          })
          .catch(err => console.error("Failed to fetch schedule result:", err));
      }
    } else {
      setUser(null);
    }
  }, []);

  const handleCellClick = (path) => {
    navigate(path); // ניווט לעמוד רלוונטי
  };

  return (
    <div className="homepage">
      <h1>Welcome, {user ? user.name : "Guest"}!</h1>
      {warning.length > 0 && (
        <div className="warning-banner">
           Partial schedule: please resubmit your availability. Problematic shifts: {warning.join(", ")}
        </div>
      )}

      <div className="table-container">
        <table className="custom-table">
          <tbody>
            <tr>
              <td onClick={() => handleCellClick('/weekleyScu')}>
                <img src={weekleyScu} alt="Weekly Schedule" />
              </td>
              {/* <td onClick={() => handleCellClick('/shiftswap')}>
                <img src={shiftswap} alt="Shift Swap" />
              </td> */}
            </tr>

            {/* <tr>
              <td onClick={() => handleCellClick('/payroll')}>
                <img src={payroll} alt="Payroll" />
              </td>
              <td onClick={() => handleCellClick('/shiftswap')}>
                <img src={payroll} alt="Payroll" />
              </td>
            </tr> */}

            {user && user.job === 'Employee' && (
              <tr>
                <td onClick={() => handleCellClick('/EmployeeRequest')}>
                  <img src={Employee_Request} alt="Employee Request" />
                </td>
              </tr>
            )}

            {user && user.job === 'management' && (
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
