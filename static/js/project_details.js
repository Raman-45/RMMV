/**
 * RMMV Dashboard — Project Details Javascript
 * 
 * Extracts data from the JSON script block and initializes the activity chart.
 */
document.addEventListener('DOMContentLoaded', function () {
    var dataElement = document.getElementById('chart-data');
    if (dataElement) {
        try {
            var chartData = JSON.parse(dataElement.textContent);
            
            // Check if initActivityChart exists (should be defined in charts.js)
            if (typeof initActivityChart === 'function') {
                initActivityChart('activityChart', chartData.labels, chartData.targets, chartData.achieved);
            } else {
                console.warn('initActivityChart function is not defined. Ensure charts.js is loaded.');
            }
        } catch (e) {
            console.error("Error parsing chart data JSON:", e);
        }
    }
});
