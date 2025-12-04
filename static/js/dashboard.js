// static/js/dashboard.js

document.addEventListener('DOMContentLoaded', function() {
    
    // --- 1. GRÁFICO DE TORTA (GASTOS POR CATEGORÍA) ---
    const canvasTorta = document.getElementById('chartTorta');
    
    if (canvasTorta) {
        const ctxTorta = canvasTorta.getContext('2d');
        
        // Leemos los datos desde el HTML (data-attributes)
        const labels = JSON.parse(canvasTorta.dataset.labels);
        const dataValues = JSON.parse(canvasTorta.dataset.data);

        new Chart(ctxTorta, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: dataValues,
                    backgroundColor: [
                        '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40', '#C9CBCF'
                    ],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false, // Permite ajustar altura por CSS
                plugins: {
                    legend: { position: 'bottom' },
                    title: { display: false }
                }
            }
        });
    }

    const canvasDiario = document.getElementById('chartDiario');
    
    if (canvasDiario) {
        const ctxDiario = canvasDiario.getContext('2d');
        
        const labels = JSON.parse(canvasDiario.dataset.labels);
        const values = JSON.parse(canvasDiario.dataset.values);

        new Chart(ctxDiario, {
            type: 'line', // Gráfico de línea
            data: {
                labels: labels,
                datasets: [{
                    label: 'Gasto Diario ($)',
                    data: values,
                    borderColor: '#36A2EB', // Azul
                    backgroundColor: 'rgba(54, 162, 235, 0.1)', // Relleno suave
                    borderWidth: 2,
                    pointRadius: 3,
                    fill: true, // Rellenar área bajo la curva
                    tension: 0.3 // Curva suave (bezier)
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: { beginAtZero: true },
                    x: { grid: { display: false } } // Quitar grilla vertical para limpieza
                },
                plugins: {
                    legend: { display: false } // No necesitamos leyenda si es solo una línea
                }
            }
            });
            }

    // --- 2. GRÁFICO DE BARRAS (EVOLUCIÓN SEMESTRAL) ---
    const canvasBarras = document.getElementById('chartBarras');
    
    if (canvasBarras) {
        const ctxBarras = canvasBarras.getContext('2d');
        
        const labels = JSON.parse(canvasBarras.dataset.labels);
        const ingresos = JSON.parse(canvasBarras.dataset.ingresos);
        const gastos = JSON.parse(canvasBarras.dataset.gastos);

        new Chart(ctxBarras, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Ingresos',
                        data: ingresos,
                        backgroundColor: '#198754', // Verde Bootstrap Success
                        borderRadius: 4
                    },
                    {
                        label: 'Gastos',
                        data: gastos,
                        backgroundColor: '#dc3545', // Rojo Bootstrap Danger
                        borderRadius: 4
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: { beginAtZero: true }
                },
                plugins: {
                    legend: { position: 'bottom' }
                }
            }
        });
    }
});