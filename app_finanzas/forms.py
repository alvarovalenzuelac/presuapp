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

    def clean_monto(self):
        monto = self.cleaned_data.get('monto')
        
        # Validamos que no sea negativo
        if monto is not None and monto < 0:
            # Opción A: Convertirlo a positivo automáticamente (Amigable)
            # return abs(monto) 
            
            # Opción B: Mostrar error (Estricto - RECOMENDADO para evitar errores de dedo)
            raise forms.ValidationError("El monto debe ser un valor positivo (ej: 25000).")
            
        return monto

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

    def __init__(self, user, *args, **kwargs):
        self.user = user  # Guardamos el usuario para usarlo en las validaciones
        super().__init__(*args, **kwargs)
        
        # Filtramos el desplegable: Solo mostramos Categorías PADRES
        self.fields['categoria_padre'].queryset = Categoria.objects.filter(
            categoria_padre=None
        ).filter(
            Q(usuario=None) | Q(usuario=user)
        ).order_by('nombre')
    
    def clean(self):
        cleaned_data = super().clean()
        nombre = cleaned_data.get('nombre')
        categoria_padre = cleaned_data.get('categoria_padre')

        # Solo validamos si el usuario ingresó un nombre
        if nombre:
            # Buscamos si ya existe una categoría con ese nombre...
            duplicados = Categoria.objects.filter(
                nombre__iexact=nombre,  # iexact: ignora mayúsculas/minúsculas
                categoria_padre=categoria_padre # ...y que tenga el MISMO padre
            ).filter(
                # ...y que sea Global O del Usuario actual
                Q(usuario=None) | Q(usuario=self.user)
            )

            # Si estamos editando (no creando), excluimos la categoría actual de la búsqueda
            if self.instance.pk:
                duplicados = duplicados.exclude(pk=self.instance.pk)

            if duplicados.exists():
                # Preparamos el mensaje de error solicitado
                if categoria_padre:
                    msg = f'La categoría "{nombre}" ya existe dentro de "{categoria_padre.nombre}".'
                else:
                    msg = f'Ya existe una categoría principal llamada "{nombre}".'
                
                # Agregamos el error al campo 'nombre' para que salga en rojo en el HTML
                self.add_error('nombre', msg)
        
        return cleaned_data

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
            'monto_limite': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'step': '1'}),
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
    
    def clean_monto_limite(self):
        monto = self.cleaned_data.get('monto_limite')
        
        if monto is not None and monto < 0:
            raise forms.ValidationError("El presupuesto debe ser un valor positivo.")
            
        return monto