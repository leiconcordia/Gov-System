document.addEventListener('DOMContentLoaded', function() {
    function updateClock() {
        const now = new Date();
        const hours = String(now.getHours()).padStart(2, '0');
        const minutes = String(now.getMinutes()).padStart(2, '0');
       
        
        const timeString = `${hours}:${minutes}`;
        document.getElementById('time').textContent = timeString;
    }
    
    // Update the clock every second
    setInterval(updateClock, 1000);
    
    // Initialize the clock
    updateClock();
    
});

