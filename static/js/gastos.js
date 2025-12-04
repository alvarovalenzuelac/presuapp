document.addEventListener('DOMContentLoaded', function() {
    // Escuchamos el clic del botón "Personalizado..."
    const btnCustom = document.getElementById('btnCustom');
    
    if (btnCustom) {
        btnCustom.addEventListener('click', function() {
            const rangeDiv = document.getElementById('customRange');
            
            // Usamos clases de Bootstrap para manejar la visibilidad
            if (rangeDiv.classList.contains('d-none')) {
                rangeDiv.classList.remove('d-none');
            } else {
                rangeDiv.classList.add('d-none');
            }
        });
    }
});