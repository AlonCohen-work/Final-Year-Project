import React, { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import "../styles/Navbar.css";

const Navbar = () => {
  const [user, setUser] = useState(null);
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    // אם יש state שמועבר, נשתמש בו
    if (location.state && location.state.user) {
      setUser(location.state.user);
    } else {
      // אם לא, נבדוק את ה-localStorage
      const userData = localStorage.getItem("user");
      if (userData) {
        setUser(JSON.parse(userData));
      }
    }
  }, [location.state]); // נקשיב לשינויים ב-state

  const handleLogout = () => {
    localStorage.removeItem("user");
    setUser(null);
    navigate("/login");
  };

  const handleHomePage = () => {
    navigate("/home");
  };

  return (
    location.pathname !== "/login" && (
      <nav className="navbar">
        <button className="logout-button" onClick={handleLogout}>
          logout
        </button>

        <div className="navbar-content">
          {user ? (
            <div className="user-info">
              <span>
                <strong>Name:</strong> {user.name}
              </span>
              <span>
                <strong>Job:</strong> {user.job}
              </span>
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
