document.addEventListener('DOMContentLoaded', function() {
    const padreSelect = document.getElementById('id_categoria_padre');
    const hijoSelect = document.getElementById('id_categoria');
    const form = document.getElementById('gastoForm');
    
    // Obtenemos la URL desde el atributo del formulario HTML
    // Esto es vital porque en un archivo .js no funciona {% url %}
    const url = form.getAttribute('data-subcategorias-url');

    // Función para limpiar y deshabilitar el segundo select
    function resetHijo() {
        hijoSelect.innerHTML = '<option value="">Selecciona una opción...</option>';
        hijoSelect.disabled = true;
    }

    // Al cargar, si no hay padre seleccionado, limpiamos el hijo
    if (!padreSelect.value) {
        resetHijo();
    }

    // Escuchamos el cambio en el select Padre
    padreSelect.addEventListener('change', function() {
        const padreId = this.value;

        if (padreId) {
            // Hacemos la petición AJAX
            fetch(`${url}?padre_id=${padreId}`)
                .then(response => response.json())
                .then(data => {
                    // Limpiamos el select actual
                    hijoSelect.innerHTML = '<option value="">Selecciona una opción...</option>';
                    
                    // Agregamos las nuevas opciones
                    data.forEach(item => {
                        const option = document.createElement('option');
                        option.value = item.id;
                        option.textContent = item.nombre;
                        hijoSelect.appendChild(option);
                    });

                    // Habilitamos el select
                    hijoSelect.disabled = false;
                })
                .catch(error => console.error('Error:', error));
        } else {
            resetHijo();
        }
    });
});