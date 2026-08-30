from math import radians, sin, cos, asin, sqrt

def distance_km(lat1, lon1, lat2, lon2) -> float:
    r = 6371.0088
    dlat = radians(lat2-lat1)
    dlon = radians(lon2-lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dlon/2)**2
    return 2*r*asin(sqrt(a))
