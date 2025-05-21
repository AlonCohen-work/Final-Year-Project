import React, { useEffect, useState } from 'react';
import '../styles/WeekleyScu.css';

const SHIFTS = ['Morning', 'Afternoon', 'Evening'];

const getStartOfWeekFromYYYYMMDD = (yyyyMmDdStr) => {
  if (!yyyyMmDdStr || !/^\d{4}-\d{2}-\d{2}$/.test(yyyyMmDdStr)) return null;
  const parts = yyyyMmDdStr.split('-');
  return new Date(parseInt(parts[0], 10), parseInt(parts[1], 10) - 1, parseInt(parts[2], 10));
};

const getWeekDateRangeStringForDisplay = (startDate) => {
  if (!startDate) return 'Date not available';

  let start;
  if (typeof startDate === 'string') {
    start = getStartOfWeekFromYYYYMMDD(startDate);
    if (!start) return 'Invalid date';
  } else if (startDate instanceof Date) {
    start = new Date(startDate);
  } else {
    return 'Unknown date';
  }

  start.setHours(0, 0, 0, 0);
  const end = new Date(start);
  end.setDate(start.getDate() + 6);

  const formatDate = (dateObj) => {
    const day = String(dateObj.getDate()).padStart(2, '0');
    const month = String(dateObj.getMonth() + 1).padStart(2, '0');
    const year = dateObj.getFullYear();
    return `${day}/${month}/${year}`;
  };

  return `${formatDate(start)} - ${formatDate(end)}`;
};

// תיקון: הפונקציה מחשבת את ראשון הבא אחרי generatedAt, לא את הקודם
const getWeekRangeFromGeneratedAt = (generatedAt) => {
  const date = new Date(generatedAt);
  const day = date.getDay(); // 0 = Sunday, ..., 6 = Saturday

  // חשב את ראשון הבא אחרי התאריך (או היום אם זה ראשון)
  const daysToAdd = day === 0 ? 0 : 7 - day;
  const sunday = new Date(date);
  sunday.setDate(sunday.getDate() + daysToAdd);
  sunday.setHours(0, 0, 0, 0);

  const saturday = new Date(sunday);
  saturday.setDate(sunday.getDate() + 6);

  const format = (d) => {
    const dd = String(d.getDate()).padStart(2, '0');
    const mm = String(d.getMonth() + 1).padStart(2, '0');
    const yyyy = d.getFullYear();
    return `${dd}/${mm}/${yyyy}`;
  };

  return `${format(sunday)} - ${format(saturday)}`;
};

const WeeklySchedule = () => {
  const [schedules, setSchedules] = useState({ latest: null, previous: [] });
  const [selectedScheduleKey, setSelectedScheduleKey] = useState('latest');
  const [idToName, setIdToName] = useState({});
  const [viewMode, setViewMode] = useState('byDay');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  // Load user once
  const [user] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem('user'));
    } catch {
      return null;
    }
  });
  const hotelName = user?.Workplace || '';

  useEffect(() => {
  if (!user) {
    setIsLoading(false);
    return;
  }
  if (!hotelName) {
    setError('User has no assigned workplace');
    setIsLoading(false);
    return;
  }

  setIsLoading(true);
  setError(null);

  fetch(`/api/generated-schedules/${encodeURIComponent(hotelName)}`)
    .then((res) => {
      if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
      return res.json();
    })
    .then((data) => {
      const latestSchedule = data?.now || null;
      const previousSchedules = Array.isArray(data?.old) ? data.old : [];
      const allSchedules = [];

      if (latestSchedule) allSchedules.push({ key: 'latest', schedule: latestSchedule });
      previousSchedules.forEach((sch, idx) => allSchedules.push({ key: idx, schedule: sch }));

      // פונקציה שעוזרת לבדוק אם תאריך נמצא בטווח שבוע
      const isDateInWeekRange = (dateToCheck, weekStartDate) => {
        if (!weekStartDate) return false;
        const start = new Date(weekStartDate);
        start.setHours(0,0,0,0);
        const end = new Date(start);
        end.setDate(start.getDate() + 6);
        return dateToCheck >= start && dateToCheck <= end;
      };

      const today = new Date();
      today.setHours(0,0,0,0);

      // מחפשים את המשמרת המכסה את השבוע הנוכחי לפי תאריך היום
      let foundKey = null;
      for (const item of allSchedules) {
        const weekStartStr = item.schedule?.relevantWeekStartDate;
        if (weekStartStr && isDateInWeekRange(today, weekStartStr)) {
          foundKey = item.key;
          break;
        }
      }

      setSchedules({
        latest: latestSchedule,
        previous: previousSchedules,
      });

      setIdToName(data.idToName || {});

      // בחר את המשמרת שמתאימה לשבוע הנוכחי (או latest אם לא נמצאה)
      setSelectedScheduleKey(foundKey !== null ? foundKey : 'latest');
    })
    .catch((err) => {
      console.error('Error loading schedules:', err);
      setError('Failed to load schedules. Please try again later.');
      setSchedules({ latest: null, previous: [] });
    })
    .finally(() => setIsLoading(false));
}, [user, hotelName]);


  const getWorkerClass = (name) => {
    if (!name || name === 'Empty' || String(name).startsWith('ID: -')) return 'worker-missing';
    if (name === user.name) return 'highlight-user';
    return 'worker-ok';
  };

  const handleSelectSchedule = (key) => {
    setSelectedScheduleKey(key);
  };

  // Determine which schedule to show
  let currentScheduleToDisplay = null;
  if (selectedScheduleKey === 'latest') {
    currentScheduleToDisplay = schedules.latest;
  } else if (
    Array.isArray(schedules.previous) &&
    typeof selectedScheduleKey === 'number' &&
    schedules.previous[selectedScheduleKey]
  ) {
    currentScheduleToDisplay = schedules.previous[selectedScheduleKey];
  }

  const previousSchedules = Array.isArray(schedules.previous) ? schedules.previous : [];

  const renderDayTable = (day, shifts) => {
    const positionsSet = new Set();
    SHIFTS.forEach((shift) => {
      (shifts[shift] || []).forEach((entry) => positionsSet.add(entry.position));
    });
    const positions = Array.from(positionsSet);

    return (
      <div className="day-section" key={day}>
        <h3>{day}</h3>
        <table className="schedule-grid">
          <thead>
            <tr>
              <th>Position</th>
              {SHIFTS.map((shift) => (
                <th key={shift}>{shift}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {positions.map((position) => (
              <tr key={position}>
                <td>{position}</td>
                {SHIFTS.map((shift) => {
                  const entries = (shifts[shift] || []).filter((e) => e.position === position);
                  const names = entries
                    .map((entry) => idToName?.[String(entry.worker_id)] ?? `ID: ${entry.worker_id}`)
                    .join(', ');
                  return (
                    <td key={shift} className={getWorkerClass(names)}>
                      {names}
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
    if (!schedule || !schedule.schedule) return <p>No schedule found</p>;

    const days = Object.keys(schedule.schedule);

    return SHIFTS.map((shift) => {
      const positionsSet = new Set();
      days.forEach((day) => {
        (schedule.schedule[day][shift] || []).forEach((entry) => {
          positionsSet.add(entry.position);
        });
      });

      const positions = Array.from(positionsSet);

      return (
        <div className="day-section" key={shift}>
          <h3>{shift} Shift – Weekly View</h3>
          <table className="schedule-grid">
            <thead>
              <tr>
                <th>Position</th>
                {days.map((day) => (
                  <th key={day}>{day}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {positions.map((position) => (
                <tr key={position}>
                  <td>{position}</td>
                  {days.map((day) => {
                    const entries = (schedule.schedule[day][shift] || []).filter((e) => e.position === position);
                    const names = entries
                      .map((entry) => {
                        const worker = idToName?.[String(entry.worker_id)];
                        return worker || `ID: ${entry.worker_id}`;
                      })
                      .join(', ');
                    return (
                      <td key={day} className={getWorkerClass(names)}>
                        {names}
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

  if (isLoading) return <div className="loading-message">Loading schedules...</div>;
  if (error) return <div className="error-message">{error}</div>;
  if (!hotelName && user) return <div className="error-message">User has no assigned workplace</div>;
  if (!user) return null;

  return (
    <div className="content-wrapper weekly-schedule-page">
      <h1>Work Schedule View - {hotelName}</h1>

      <div className="button-fixed-right">
        <button
          onClick={() => handleSelectSchedule('latest')}
          className={selectedScheduleKey === 'latest' ? 'active' : ''}
          disabled={!schedules.latest}
        >
          Show Current Schedule
          {schedules.latest?.relevantWeekStartDate &&
            ` (${getWeekDateRangeStringForDisplay(schedules.latest.relevantWeekStartDate)})`}
        </button>

        {previousSchedules.map((prevSchedule, index) => (
          <button
            key={prevSchedule._id || index}
            onClick={() => handleSelectSchedule(index)}
            className={selectedScheduleKey === index ? 'active' : ''}
          >
            {index + 1} Week Back
            {prevSchedule.relevantWeekStartDate &&
              ` (${getWeekDateRangeStringForDisplay(prevSchedule.relevantWeekStartDate)})`}
          </button>
        ))}

        {currentScheduleToDisplay && (
          <button
            onClick={() => setViewMode((prevMode) => (prevMode === 'byDay' ? 'wide' : 'byDay'))}
            className="btn btn-toggle"
          >
            {viewMode === 'byDay' ? '🔄 Show by Week' : '📅 Show by Day'}
          </button>
        )}
      </div>

      {currentScheduleToDisplay?.schedule && (
        <div className="schedule-content">
          <p style={{ textAlign: 'center', fontSize: '0.9em', color: '#555' }}>
            Schedule for: {getWeekRangeFromGeneratedAt(currentScheduleToDisplay.generatedAt)}
            {currentScheduleToDisplay.status === 'partial' && (
              <span style={{ color: 'orange', marginLeft: '10px' }}>(Partial schedule)</span>
            )}
          </p>

          {viewMode === 'byDay'
            ? Object.entries(currentScheduleToDisplay.schedule).map(([day, shifts]) =>
                renderDayTable(day, shifts)
              )
            : renderWideTable(currentScheduleToDisplay)}
        </div>
      )}
    </div>
  );
};

export default WeeklySchedule;
