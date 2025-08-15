document.addEventListener("DOMContentLoaded", function() {
    const chartElement = document.getElementById('incomeChart');
    if (!chartElement) return;

    // Fetch chart data from the json_script element
    const chartData = JSON.parse(document.getElementById('income-chart-data').textContent);

    // Ensure labels and data exist
    chartData.labels = chartData.labels || [];
    chartData.data = chartData.data || [];

    new Chart(chartElement.getContext('2d'), {
        type: 'line',
        data: {
            labels: chartData.labels,
            datasets: [{
                label: 'Salary Income',
                data: chartData.data,
                borderColor: 'rgba(75, 192, 192, 1)',
                backgroundColor: 'rgba(75, 192, 192, 0.2)',
                fill: true,
                tension: 0.3
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
});
