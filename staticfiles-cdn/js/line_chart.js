document.addEventListener("DOMContentLoaded", function() {
    const canvas = document.getElementById("spendingChart");
    if (!canvas) return;  // No chart to render

    // Read data from data-* attributes
    const periods = JSON.parse(canvas.dataset.periods);
    const datasets = JSON.parse(canvas.dataset.datasets);

    const ctx = canvas.getContext("2d");

    new Chart(ctx, {
        type: "line",
        data: {
            labels: periods,
            datasets: datasets
        },
        options: {
            responsive: true,
            interaction: { mode: "index", intersect: false },
            plugins: {
                title: {
                    display: true,
                    text: "Spending Trend for Top 10 Categories"
                }
            },
            scales: { y: { beginAtZero: true } }
        }
    });
});
