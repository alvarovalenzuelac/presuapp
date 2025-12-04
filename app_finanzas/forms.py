from django import forms
from django.db.models import Q
from django.utils import timezone
from .models import Transaccion, Categoria,Presupuesto

class SubcategoriaChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return obj.nombre

class TransaccionForm(forms.ModelForm):
    # Campo extra solo para la UI
    categoria_padre = forms.ModelChoiceField(
        queryset=Categoria.objects.none(),
        label="Categoría Principal",
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    categoria = SubcategoriaChoiceField(
        queryset=Categoria.objects.none(),
        label="Subcategoría",
        required=True, # La subcategoría es obligatoria para guardar
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = Transaccion
        fields = ['tipo', 'monto', 'fecha', 'categoria_padre', 'categoria', 'descripcion']
        widgets = {
            # FORMATO DE FECHA CRÍTICO PARA NAVEGADORES
            'fecha': forms.DateInput(
                format='%Y-%m-%d',
                attrs={'type': 'date', 'class': 'form-control'}
            ),
            'descripcion': forms.TextInput(attrs={'placeholder': 'Ej: Supermercado Lider', 'class': 'form-control'}),
            'monto': forms.NumberInput(attrs={'class': 'form-control'}),
            'tipo': forms.Select(attrs={'class': 'form-select'})
        }

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # --- LOGICA DE CATEGORÍA PADRE Y FILTROS ---
        
        # 1. Cargar opciones del Padre
        self.fields['categoria_padre'].queryset = Categoria.objects.filter(
            Q(usuario=None) | Q(usuario=user),
            categoria_padre=None 
        ).order_by('nombre')
        self.fields['categoria_padre'].empty_label = "Selecciona un grupo..."

        # 2. Cargar opciones del Hijo
        self.fields['categoria'].queryset = Categoria.objects.filter(
            Q(usuario=None) | Q(usuario=user)
        ).exclude(categoria_padre=None).order_by('nombre')
        self.fields['categoria'].empty_label = "Selecciona una opción..."

        # --- VALORES POR DEFECTO (CREAR NUEVO) ---
        if not self.instance.pk:
            self.fields['tipo'].initial = 'GASTO'
            self.fields['fecha'].initial = timezone.now().date() # Hoy
        
        # --- VALORES AL EDITAR ---
        if self.instance.pk:
            # Pre-llenar fecha
            if self.instance.fecha:
                self.fields['fecha'].initial = self.instance.fecha

            # Pre-llenar categorías
            if self.instance.categoria:
                padre_actual = self.instance.categoria.categoria_padre
                if padre_actual:
                    self.fields['categoria_padre'].initial = padre_actual
                
                # Filtramos la lista de hijos para mostrar solo los hermanos
                self.fields['categoria'].queryset = Categoria.objects.filter(
                    Q(usuario=None) | Q(usuario=user),
                    categoria_padre=padre_actual
                ).order_by('nombre')

class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ['nombre', 'categoria_padre']
        labels = {
            'nombre': 'Nombre de la Subcategoría',
            'categoria_padre': 'Pertenece a la Categoría'
        }
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Netflix, Uber, Cerveza'}),
            'categoria_padre': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtramos el desplegable: Solo mostramos Categorías PADRES (las que no tienen padre)
        # y que sean globales (usuario=None)
        self.fields['categoria_padre'].queryset = Categoria.objects.filter(
            categoria_padre=None, 
            usuario=None
        ).order_by('nombre')

class PresupuestoForm(forms.ModelForm):
    # Selector de Meses con nombres en español
    MESES_CHOICES = [
        (1, 'Enero'), (2, 'Febrero'), (3, 'Marzo'), (4, 'Abril'),
        (5, 'Mayo'), (6, 'Junio'), (7, 'Julio'), (8, 'Agosto'),
        (9, 'Septiembre'), (10, 'Octubre'), (11, 'Noviembre'), (12, 'Diciembre')
    ]
    
    nombre = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Salidas Fin de Semana'}))
    mes = forms.ChoiceField(choices=MESES_CHOICES, widget=forms.Select(attrs={'class': 'form-select'}))
    anio = forms.IntegerField(widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 2025'}))

    # Filtramos categorías igual que antes (Padres globales o del usuario)
    categorias = forms.ModelMultipleChoiceField(
        queryset=Categoria.objects.none(),
        required=False,
        label="Selecciona las Categorías",
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'list-unstyled'})
    )


    class Meta:
        model = Presupuesto
        fields = ['nombre', 'monto_limite', 'mes', 'anio', 'categorias']
        widgets = {
            'monto_limite': forms.NumberInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        hoy = timezone.now()
        
        # Valores por defecto
        if not self.instance.pk:
            self.fields['mes'].initial = hoy.month
            self.fields['anio'].initial = hoy.year

        # Filtro de categorías: Solo PADRES (para simplificar presupuestos) 
        # Es raro hacer presupuesto solo de "Uber", usualmente es de "Transporte"
        self.fields['categorias'].queryset = Categoria.objects.filter(
            Q(usuario=None) | Q(usuario=user)
        ).order_by('nombre')