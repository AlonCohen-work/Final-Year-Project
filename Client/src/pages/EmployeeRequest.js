import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import "../styles/EmployeeRequest.css";

const EmployeeRequest = () => {
  const [userId, setUserId] = useState(null); // משתנה מצב לשמירת ה-ID של המשתמש
  const [selectedDays, setSelectedDays] = useState([]);
  const navigate = useNavigate();

  // קריאת נתוני המשתמש מ-localStorage בטעינת הקומפוננטה
  useEffect(() => {
    const userData = JSON.parse(localStorage.getItem("user"));
    if (userData && userData.id) {
      setUserId(userData.id); // שמירת ה-ID במצב
    } else {
      console.error("User data not found in localStorage.");
      navigate("/login"); // אם לא נמצא משתמש, להפנות לעמוד ההתחברות
    }
  }, [navigate]);

  const daysOfWeek = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];

  const handleCheckboxChange = (day) => {
    setSelectedDays((prevSelectedDays) =>
      prevSelectedDays.includes(day)
        ? prevSelectedDays.filter((d) => d !== day) // Remove the day
        : [...prevSelectedDays, day] // Add the day
    );
  };

  const handleSend = async () => {
    if (!userId) {
      console.error("User ID is not defined.");
      return;
    }

    try {
      const response = await fetch("/EmployeeRequest", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          userId,
          selectedDays,
        }),
      });

      if (response.ok) {
        console.log("Data sent successfully.");
        navigate("/home"); // מעבר לעמוד הבית
      } else {
        const errorMessage = await response.text();
        console.error("Server response:", errorMessage);
      }
    } catch (error) {
      console.error("An error occurred:", error);
    }
  };

  return (
    <div className="employee-request">
      <h1>Employee Request</h1>
      <p>Select the days you are available:</p>
      <table className="availability-table">
        <thead>
          <tr>
            <th>Day</th>
            <th>Available</th>
          </tr>
        </thead>
        <tbody>
          {daysOfWeek.map((day) => (
            <tr key={day} className={selectedDays.includes(day) ? "selected-row" : ""}>
              <td>{day}</td>
              <td>
                <input
                  type="checkbox"
                  id={`checkbox-${day}`}
                  name={`available-${day}`}
                  onChange={() => handleCheckboxChange(day)}
                  checked={selectedDays.includes(day)}
                />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <button className="send-button" onClick={handleSend}>
        Send
      </button>
    </div>
  );
};

export default EmployeeRequest;
