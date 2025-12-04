document.addEventListener('DOMContentLoaded', function () {
    var deleteModal = document.getElementById('deleteGastoModal');
    
    if (deleteModal) {
        deleteModal.addEventListener('show.bs.modal', function (event) {
            var button = event.relatedTarget; 
            
            var urlEliminar = button.getAttribute('data-url');
            var descripcion = button.getAttribute('data-descripcion');
            
            var modalDescripcion = deleteModal.querySelector('#modalDescripcionGasto');
            var modalBtnConfirmar = deleteModal.querySelector('#btnConfirmarEliminarGasto');

            modalDescripcion.textContent = descripcion;
            modalBtnConfirmar.setAttribute('href', urlEliminar);
        });
    }
});