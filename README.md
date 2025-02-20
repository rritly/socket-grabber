# socket-grabber
Принимает и передает данные по socket TCP.   

Протокол обмена:
```
{
    "READ": {
        "top.autoEn": bool,
        "top.status": int,
        "top.distanceL1": int,
        "top.distanceL2": int,
        "top.speed": int,
        "top.currDistance": int,
        "top.currMoisture": int,
        "top.arrayMoisture": list[float],
        "bottom.autoEn": bool,
        "bottom.status": int,
        "bottom.distanceL1": int,
        "bottom.distanceL2": int,
        "bottom.speed": int,
        "bottom.currDistance": int,
        "bottom.currMoisture": int,
        "bottom.arrayMoisture": list[float],
    },
    "WRITE": {
        "airBlower": bool,
        "top.jogForward": bool,
        "top.jogBackward": bool,
        "top.width": int,
        "top.delay": int,
        "top.speed": int,
        "top.speedJog": int,
        "top.speedInitia": int,
        "top.pulsesPerMeter": int,
        "top.offsetCenter": int,
        "bottom.jogForward": bool,
        "bottom.jogBackward": bool,
        "bottom.width": int,
        "bottom.delay": int,
        "bottom.speed": int,
        "bottom.speedJog": int,
        "bottom.speedInitia": int,
        "bottom.pulsesPerMeter": int,
        "bottom.offsetCenter": int,
    },
}
```    
