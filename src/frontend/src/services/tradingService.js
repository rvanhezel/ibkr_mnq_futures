const API_URL = 'http://localhost:5000/api';

export const getStatus = async () => {
    try {
        const response = await fetch(`${API_URL}/status`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Error fetching status:', error);
        throw error;
    }
};

export const startTrading = async () => {
    try {
        const response = await fetch(`${API_URL}/start`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
        });
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Error starting trading:', error);
        throw error;
    }
};

export const stopTrading = async () => {
    try {
        const response = await fetch(`${API_URL}/stop`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
        });
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Error stopping trading:', error);
        throw error;
    }
};

export const reinitializeDatabase = async () => {
    try {
        const response = await fetch(`${API_URL}/reinitialize-db`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || `HTTP error! status: ${response.status}`);
        }
        return data;
    } catch (error) {
        console.error('Error reinitializing database:', error);
        throw error;
    }
}; 