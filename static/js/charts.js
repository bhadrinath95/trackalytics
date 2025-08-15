document.addEventListener("DOMContentLoaded", function () {
    console.log("Chart data:", window.chartData); // Debug

    if (!window.chartData) return;

    Object.values(window.chartData).forEach(data => {
        const ctx = document.getElementById(`chart-${data.i}`);
        if (!ctx) return;

        new Chart(ctx.getContext('2d'), {
            type: 'pie',
            data: {
                labels: data.labels,
                datasets: [{
                    label: 'Spending by Category',
                    data: data.data,
                    backgroundColor: data.colors
                }]
            }
        });
    });
});
