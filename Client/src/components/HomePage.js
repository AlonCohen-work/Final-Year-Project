import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import "../styles/HomePage.css";

import payroll from "../images/payroll.png";
import shiftswap from "../images/shiftswap.png";
import weekleyScu from "../images/weekleyScu.png";
import ManageHours from "../images/ManageHours.png";
import Employee_Request from "../images/iconapp-Photo.png";


const HomePage = () => {
  const [user, setUser] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    const userData = localStorage.getItem("user");
    if (userData) {
      setUser(JSON.parse(userData));
    } else {
      // Redirect to login page if no user data found in localStorage
      navigate("/login");
    }
  }, [navigate]);
  
  const handleCellClick = (path) => {
    navigate(path); // Navigate to the passed path
  };

  return (
    <div className="homepage">
      
      <h1>Welcome, {user ? user.name : "Guest"}!</h1>

      <div className="table-container">
        <table className="custom-table">
          <tbody>
            <tr>
              <td onClick={() => handleCellClick('/weekleyScu')}>
                <img src={weekleyScu} alt="Weekly Schedule" />
              </td>
              <td onClick={() => handleCellClick('/shiftswap')}>
                <img src={shiftswap} alt="Shift Swap" />
              </td>
            </tr>
            <tr>
              <td onClick={() => handleCellClick('/payroll')}>
                <img src={payroll} alt="Payroll" />
              </td>
              <td onClick={() => handleCellClick('/shiftswap')}>
              <img src={payroll} alt="Payroll" />
              </td>
            </tr>
            {user && user.job === 'Employee' && (
              <tr>
               <td onClick={() => handleCellClick('/EmployeeRequest')}>
           <img src={Employee_Request} alt="EmployeeRequest" />
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
