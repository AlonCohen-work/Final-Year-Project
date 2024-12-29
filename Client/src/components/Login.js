import React, { useState } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";
import "../styles/Login.css";

const Login = () => {
  const [id, setId] = useState("");
  const [password, setPassword] = useState("");
  const navigate = useNavigate();

  const handleLogin = (e) => {
    e.preventDefault();

    axios
      .post("http://localhost:3002/login", {
        id: parseInt(id), // Convert ID to Number
        password,
      })
      .then((response) => {
        if (response.data.success) {
          localStorage.setItem(
            "user",
            JSON.stringify({
              id: response.data.id,
              job: response.data.job,
              name: response.data.name,
            })
          );
          navigate("/home");
        } else {
          alert("Invalid ID or password");
        }
      })
      .catch((error) => {
        console.error("Login error", error);
        alert("An error occurred. Please try again.");
      });
  };

  return (
    <div className="login-container">
      <form className="login-form" onSubmit={handleLogin}>
        <h2>Login Page</h2>
        <label htmlFor="id">Id Number</label>
        <input
          type="text"
          id="id"
          value={id}
          onChange={(e) => setId(e.target.value)}
          required
        />
        <label htmlFor="password">Password</label>
        <input
          type="password"
          id="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
        <button type="submit">Login</button>
      </form>
    </div>
  );
};

export default Login;
