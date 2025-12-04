document.addEventListener('DOMContentLoaded', function() {
    
    // 1. MANEJO DEL MODAL DE CONFLICTO
    const modalEl = document.getElementById('modalConflicto');
    
    if (modalEl) {
        // Leemos el atributo data-mostrar que pusimos en el HTML
        const debeMostrar = modalEl.getAttribute('data-mostrar') === 'true';
        
        if (debeMostrar) {
            const modal = new bootstrap.Modal(modalEl);
            modal.show();
        }
    }

    // 2. MANEJO DEL BOTÓN "SÍ, REEMPLAZAR"
    const btnReemplazar = document.getElementById('btnConfirmarReemplazo');
    
    if (btnReemplazar) {
        btnReemplazar.addEventListener('click', function() {
            // Cambiamos el valor del input oculto
            const inputConfirmar = document.getElementById('inputConfirmar');
            if (inputConfirmar) {
                inputConfirmar.value = "si";
            }
            
            // Enviamos el formulario
            const form = document.getElementById('formPresupuesto');
            if (form) {
                form.submit();
            }
        });
    }
});