document.addEventListener('DOMContentLoaded', function () {
    var deleteModal = document.getElementById('deleteModal');
    
    if (deleteModal) {
        // Escuchamos el evento cuando el modal se está abriendo
        deleteModal.addEventListener('show.bs.modal', function (event) {
            // Botón que activó el modal
            var button = event.relatedTarget; 
            
            // Extraemos la info de los atributos data-*
            var urlEliminar = button.getAttribute('data-url');
            var nombreCategoria = button.getAttribute('data-nombre');
            
            // Actualizamos el contenido del modal
            var modalNombre = deleteModal.querySelector('#modalNombreCategoria');
            var modalBtnConfirmar = deleteModal.querySelector('#btnConfirmarEliminar');

            modalNombre.textContent = nombreCategoria;
            modalBtnConfirmar.setAttribute('href', urlEliminar);
        });
    }
});