from django.http import JsonResponse

def buscar_municipios(request):
    term = request.GET.get('term', '').lower()
    
    municipios = [
        # muni
        "Zipaquirá, Cundinamarca", "Chía, Cundinamarca", "Cajicá, Cundinamarca", 
        "Cogua, Cundinamarca", "Nemocón, Cundinamarca", "Sopó, Cundinamarca", 
        "Tocancipá, Cundinamarca", "Gachancipá, Cundinamarca", "Pacho, Cundinamarca",
        "Facatativá, Cundinamarca", "Fusagasugá, Cundinamarca", "Soacha, Cundinamarca", 
        "Madrid, Cundinamarca", "Funza, Cundinamarca", "Mosquera, Cundinamarca", 
        "Tabio, Cundinamarca", "Tenjo, Cundinamarca", "Cota, Cundinamarca",
        
        #   Ciudades
        "Bogotá, D.C.", "Medellín, Antioquia", "Cali, Valle del Cauca", 
        "Barranquilla, Atlántico", "Cartagena, Bolívar", "Cúcuta, Norte de Santander", 
        "Bucaramanga, Santander", "Ibagué, Tolima", "Santa Marta, Magdalena", 
        "Villavicencio, Meta", "Pereira, Risaralda", "Manizales, Caldas", 
        "Armenia, Quindío", "Pastos, Nariño", "Neiva, Huila", "Popayán, Cauca",
        "Montería, Córdoba", "Sincelejo, Sucre", "Valledupar, Cesar", "Tunja, Boyacá"
    ]
    
    
    res = [m for m in municipios if term in m.lower()]
    
    
    return JsonResponse(res[:15], safe=False)