"""Send an SMS to the nearest ranger post when a fence sensor fires near a rhino area."""
import json, urllib.request

RHINO_ZONES = {"Kaziranga-E": (26.66, 93.53), "Pobitora": (26.23, 92.05)}

def nearest_post(lat, lon, posts):
    return min(posts, key=lambda p: (p["lat"] - lat) ** 2 + (p["lon"] - lon) ** 2)

def alert(event, posts, send):
    """event: {zone, lat, lon, time}. Greater one-horned rhinos are poached for horn."""
    if event["zone"] in RHINO_ZONES:
        p = nearest_post(event["lat"], event["lon"], posts)
        send(p["phone"], f"Fence alarm in {event['zone']} at {event['time']}: possible poachers")
