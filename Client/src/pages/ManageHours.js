import React, { useState } from 'react';
import '../styles/ManageHours.css';

const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];

const shifts = ['Morning', 'Afternoon', 'Evening'];

const positions = [
  'Main Entrance Guard',
  'Lobby Security Officer',
  'Parking Lot Security',
  'Security Control Room Operator',
  'Floor Patrol Guard',
  'Event Hall Security',
  'Pool Area Guard',
  'Beach Security',
  'Back Entrance Guard',
  'Loading Dock Security',
  'CCTV Surveillance Operator',
  'Security Supervisor',
  'Weapons Inspection Officer',
  'Garage/Basement Patrol',
  'Fire Safety & Evacuation Monitor'
];

// יצירת מצב ראשוני
const createInitialSchedule = () => {
  const schedule = {};
  shifts.forEach((shift) => {
    schedule[shift] = {};
    positions.forEach((position) => {
      schedule[shift][position] = {
        weapon: false,
      };
      days.forEach((day) => {
        schedule[shift][position][day] = {
          active: false,
          numOfEmployees: 0,
        };
      });
    });
  });
  return schedule;
};

const ManageHours = () => {
  const [schedule, setSchedule] = useState(createInitialSchedule());

  // שינוי שדה (עובדים / פעיל)
  const handleChange = (shift, position, day, field, value) => {
    setSchedule((prev) => ({
      ...prev,
      [shift]: {
        ...prev[shift],
        [position]: {
          ...prev[shift][position],
          [day]: {
            ...prev[shift][position][day],
            [field]: value,
          },
        },
      },
    }));
  };

  // שינוי נשק לכל עמדה
  const handleWeaponToggle = (shift, position, value) => {
    setSchedule((prev) => ({
      ...prev,
      [shift]: {
        ...prev[shift],
        [position]: {
          ...prev[shift][position],
          weapon: value,
        },
      },
    }));
  };

  return (
    <div className="manage-hours-container">
      <div className="manage-hours-form">
        <h2>Manage Schedule</h2>
        {shifts.map((shift) => (
          <div key={shift}>
            <h3>{shift} Shift</h3>
            <table className="schedule-table">
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
                    <td>
                      {position}
                      <label style={{ marginLeft: '10px' }}>
                        <input
                          type="checkbox"
                          checked={schedule[shift][position].weapon}
                          onChange={(e) =>
                            handleWeaponToggle(shift, position, e.target.checked)
                          }
                        />{' '}
                        Weapon
                      </label>
                    </td>
                    {days.map((day) => (
                      <td key={`${shift}-${position}-${day}`}>
                        <input
                          type="number"
                          min="0"
                          value={schedule[shift][position][day].numOfEmployees}
                          placeholder="#"
                          onChange={(e) =>
                            handleChange(
                              shift,
                              position,
                              day,
                              'numOfEmployees',
                              parseInt(e.target.value) || 0
                            )
                          }
                          style={{ width: '40px', marginRight: '5px' }}
                        />
                        <input
                          type="checkbox"
                          checked={schedule[shift][position][day].active}
                          onChange={(e) =>
                            handleChange(
                              shift,
                              position,
                              day,
                              'active',
                              e.target.checked
                            )
                          }
                        />
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))}
        <button className="save-all">Save All</button>
      </div>
    </div>
  );
};

export default ManageHours;
