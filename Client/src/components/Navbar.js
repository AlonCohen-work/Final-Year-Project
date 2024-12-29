import React, { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import "../styles/Navbar.css";

const Navbar = () => {
  const [user, setUser] = useState(null);
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    const userData = localStorage.getItem("user");
    if (userData) {
      setUser(JSON.parse(userData));
    }
  }, []);

  const handleLogout = () => {
    localStorage.removeItem("user"); // מחיקת נתוני המשתמש מ-localStorage
    setUser(null); // עדכון ה-state של המשתמש
    navigate("/login"); // חזרה לעמוד ההתחברות
  };

  const handleHomePage = () => {
    navigate("/home"); // ניווט לעמוד הבית
  };

  return (
    location.pathname !== "/login" && ( // אם לא בעמוד ההתחברות, להציג את ה-Navbar
      <nav className="navbar">
        <button className="logout-button" onClick={handleLogout}>
          logout
        </button>

        <div className="navbar-content">
          {user ? (
            <div className="user-info">
              <span><strong>Name:</strong> {user.name}</span>
              <span><strong>Job:</strong> {user.job}</span>
            </div>
          ) : (
            <span></span>
          )}
        </div>

        <div className="navbar-right">
          <button className="home-button" onClick={handleHomePage}>
            home
          </button>
        </div>
      </nav>
    )
  );
};

export default Navbar;
