import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import '../styles/WeekleyScu.css';

const SHIFTS = ['Morning', 'Afternoon', 'Evening'];

const WeekleyScu = () => {
  const navigate = useNavigate();
  const [schedules, setSchedules] = useState({ latest: null, previous: null });
  const [selectedSchedule, setSelectedSchedule] = useState("A");
  const [idToName, setIdToName] = useState({});
  const [viewMode, setViewMode] = useState("byDay");

  const user = JSON.parse(localStorage.getItem("user"));

  useEffect(() => {
    if (!user || !user.Workplace) {
      navigate("/login");
      return;
    }

    fetch(`/get-full-schedules/${encodeURIComponent(user.Workplace)}`)
      .then((res) => res.json())
      .then((data) => {
        setSchedules({ latest: data.latest, previous: data.previous });
        setIdToName(data.idToName || {});
      })
      .catch((err) => console.error("Error fetching schedules and workers:", err));
  }, [navigate, user]);

  const getWorkerClass = (name) => {
    if (!name || name === "Empty") return "worker-missing";
    if (name === user.name) return "highlight-user";
    return "worker-ok";
  };

  const currentSchedule = selectedSchedule === "A" ? schedules.latest : schedules.previous;

  const renderDayTable = (day, shifts) => {
    const positionsSet = new Set();
    SHIFTS.forEach(shift => {
      (shifts[shift] || []).forEach(entry => positionsSet.add(entry.position));
    });
    const positions = Array.from(positionsSet);

    return (
      <div className="day-section" key={day}>
        <h3>{day}</h3>
        <table className="schedule-grid">
          <thead>
            <tr>
              <th>Position</th>
              {SHIFTS.map(shift => <th key={shift}>{shift}</th>)}
            </tr>
          </thead>
          <tbody>
            {positions.map(position => (
              <tr key={position}>
                <td>{position}</td>
                {SHIFTS.map(shift => {
                  const entries = (shifts[shift] || []).filter(e => e.position === position);
                  return (
                    <td key={shift}>
                      {entries.map((entry, i) => {
                        const name = idToName?.[String(entry.worker_id)];
                        const className = getWorkerClass(name);
                        return (
                          <div key={i} className={className}>
                            {name ?? `ID: ${entry.worker_id}`}
                          </div>
                        );
                      })}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  };

  const renderWideTable = (schedule) => {
    if (!schedule || !schedule.schedule) return <p>No schedule found.</p>;

    const days = Object.keys(schedule.schedule);

    return SHIFTS.map(shift => {
      const positionsSet = new Set();
      days.forEach(day => {
        (schedule.schedule[day][shift] || []).forEach(entry => {
          positionsSet.add(entry.position);
        });
      });

      const positions = Array.from(positionsSet);

      return (
        <div className="day-section" key={shift}>
          <h3>{shift} Shift – Matrix View</h3>
          <table className="schedule-grid">
            <thead>
              <tr>
                <th>Position</th>
                {days.map(day => <th key={day}>{day}</th>)}
              </tr>
            </thead>
            <tbody>
              {positions.map(position => (
                <tr key={position}>
                  <td>{position}</td>
                  {days.map(day => {
                    const entries = (schedule.schedule[day][shift] || []).filter(e => e.position === position);
                    return (
                      <td key={day}>
                        {entries.map((entry, i) => {
                          const name = idToName?.[String(entry.worker_id)];
                          const className = getWorkerClass(name);
                          return (
                            <div key={i} className={className}>
                              {name ?? `ID: ${entry.worker_id}`}
                            </div>
                          );
                        })}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
    });
  };

  return (
    <div className="content-wrapper">
      <h1>Weekly Schedule</h1>

      <div className="button-fixed-right">
        <button
          onClick={() => setSelectedSchedule("A")}
          className={selectedSchedule === "A" ? "active" : ""}
        >
          <span role="img" aria-label="Schedule A">🅰️</span> Show Schedule This Week
        </button>
        <button
          onClick={() => setSelectedSchedule("B")}
          className={selectedSchedule === "B" ? "active" : ""}
        >
          <span role="img" aria-label="Schedule B">🅱️</span> Show Schedule Previous Week
        </button>
        <button
          onClick={() => setViewMode(viewMode === "byDay" ? "wide" : "byDay")}
          className="toggle-view"
        >
          {viewMode === "byDay" ? "🔄 View as Matrix" : "📅 View by Day"}
        </button>
      </div>

      {currentSchedule?.schedule &&
        (viewMode === "byDay"
          ? Object.entries(currentSchedule.schedule).map(([day, shifts]) =>
              renderDayTable(day, shifts)
            )
          : renderWideTable(currentSchedule))}
    </div>
  );
};

export default WeekleyScu;
