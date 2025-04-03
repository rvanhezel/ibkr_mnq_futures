const API_URL = 'http://localhost:5000/api';

export const getSettings = async () => {
  try {
    console.log('Fetching settings from:', `${API_URL}/settings`);
    const response = await fetch(`${API_URL}/settings`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    console.log('Received settings:', data);
    return data;
  } catch (error) {
    console.error('Error fetching settings:', error);
    throw new Error(`Failed to fetch settings: ${error.message}`);
  }
};

export const updateSettings = async (settings) => {
  try {
    console.log('Updating settings:', settings);
    const response = await fetch(`${API_URL}/settings`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(settings),
    });
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    console.log('Settings update response:', data);
    return data;
  } catch (error) {
    console.error('Error updating settings:', error);
    throw new Error(`Failed to update settings: ${error.message}`);
  }
}; 