/* Radar Níscalo — GPS de recorridos: puntos ida/vuelta + filtro anti-deriva */
(function(){
  "use strict";

  const MAX_ACCURACY=35;
  const MIN_POINT_DISTANCE=7;
  const MIN_POINT_INTERVAL=2500;
  const MAX_WALK_SPEED=5.5;

  function dist(a,b){
    const R=6371000,rad=Math.PI/180;
    const la1=+a.lat,la2=+b.lat,lo1=+a.lon,lo2=+b.lon;
    const x=(lo2-lo1)*rad*Math.cos((la1+la2)*rad/2);
    const y=(la2-la1)*rad;
    return Math.sqrt(x*x+y*y)*R;
  }

  function limpiarPuntos(puntos){
    if(!Array.isArray(puntos)) return [];
    const salida=[];
    for(const p of puntos){
      const lat=Number(p.lat),lon=Number(p.lon);
      if(!Number.isFinite(lat)||!Number.isFinite(lon)) continue;
      const acc=Number(p.accuracy??p.precision??99);
      if(acc>MAX_ACCURACY) continue;
      const t=Number(p.timestamp)||Date.parse(p.hora)||0;
      const nuevo={lat,lon,accuracy:acc,timestamp:t};
      const ultimo=salida[salida.length-1];
      if(!ultimo){salida.push(nuevo);continue;}
      const metros=dist(ultimo,nuevo);
      const dt=t&&ultimo.timestamp?Math.max(0,(t-ultimo.timestamp)/1000):0;
      if(metros<MIN_POINT_DISTANCE) continue;
      if(dt>0 && dt<MIN_POINT_INTERVAL/1000) continue;
      if(dt>0 && metros/dt>MAX_WALK_SPEED) continue;
      salida.push(nuevo);
    }
    return salida;
  }

  function crearCapaPuntos(puntos){
    if(typeof mapa==="undefined"||!mapa) return null;
    if(typeof lineaRecorrido!=="undefined" && lineaRecorrido){
      try{mapa.removeLayer(lineaRecorrido)}catch(e){}
    }
    const grupo=L.layerGroup().addTo(mapa);
    if(!puntos.length){lineaRecorrido=grupo;return grupo;}

    let idaFin=puntos.length-1;
    if(puntos.length>=4){
      let max=0;
      for(let i=1;i<puntos.length;i++){
        const d=dist(puntos[0],puntos[i]);
        if(d>max){max=d;idaFin=i;}
      }
    }

    puntos.forEach((p,i)=>{
      const vuelta=i>idaFin;
      L.circleMarker([p.lat,p.lon],{
        radius:4.5,
        color:vuelta?"#ffffff":"#ffffff",
        weight:1.2,
        fillColor:vuelta?"#d9363e":"#2878e8",
        fillOpacity:.95,
        interactive:false,
        pane:"markerPane"
      }).addTo(grupo);
    });
    lineaRecorrido=grupo;
    return grupo;
  }

  function redibujar(puntos,ajustar){
    const filtrados=limpiarPuntos(puntos);
    crearCapaPuntos(filtrados);
    if(ajustar && filtrados.length>1){
      const bounds=L.latLngBounds(filtrados.map(p=>[p.lat,p.lon]));
      mapa.fitBounds(bounds,{padding:[30,30],maxZoom:17});
    }
    return filtrados;
  }

  window.dibujarRecorridoGuardado=function(){
    if(typeof mapa==="undefined"||!mapa) return;
    const filtrados=redibujar(window.recorridoPuntos||[],false);
    window.recorridoPuntos=filtrados;
  };

  window.dibujarRutaBiblioteca=function(r){
    if(!r||typeof mapa==="undefined"||!mapa) return;
    const filtrados=redibujar(r.puntos||[],true);
    if(typeof recorridoPuntos!=="undefined") window.recorridoPuntos=filtrados;
    const aviso=document.getElementById("recorridoAviso");
    if(aviso) aviso.textContent="Ruta «"+(r.nombre||"sin nombre")+"» cargada · 🔵 ida · 🔴 vuelta.";
  };

  window.actualizarPosicionRecorrido=function(pos){
    const lat=Number(pos.coords.latitude),lon=Number(pos.coords.longitude);
    const precision=Number(pos.coords.accuracy)||99;
    if(!Number.isFinite(lat)||!Number.isFinite(lon)||typeof mapa==="undefined"||!mapa) return;

    if(!window.marcadorRecorrido){
      window.marcadorRecorrido=L.circleMarker([lat,lon],{radius:7,color:"#fff",weight:2,fillColor:"#2878e8",fillOpacity:1,zIndexOffset:1000}).addTo(mapa);
    }else window.marcadorRecorrido.setLatLng([lat,lon]);

    if(typeof recorridoActivo==="undefined"||!recorridoActivo) return;
    if(precision>MAX_ACCURACY) return;

    const puntos=window.recorridoPuntos||[];
    const ahora=Date.now();
    const nuevo={lat:Number(lat.toFixed(6)),lon:Number(lon.toFixed(6)),precision:Math.round(precision),accuracy:Math.round(precision),hora:new Date(ahora).toISOString(),timestamp:ahora};
    const ultimo=puntos[puntos.length-1];
    if(ultimo){
      const metros=dist(ultimo,nuevo);
      const dt=ultimo.timestamp?Math.max(0,(ahora-ultimo.timestamp)/1000):0;
      if(metros<MIN_POINT_DISTANCE) return;
      if(dt>0 && dt<MIN_POINT_INTERVAL/1000) return;
      if(dt>0 && metros/dt>MAX_WALK_SPEED) return;
      window.recorridoDistancia=(Number(window.recorridoDistancia)||0)+metros;
    }
    puntos.push(nuevo);
    window.recorridoPuntos=puntos;
    crearCapaPuntos(puntos);
    if(typeof actualizarPanelRecorrido==="function") actualizarPanelRecorrido();
    if(typeof guardarRecorridoLocal==="function") guardarRecorridoLocal();
  };

  /* Al cargar una ruta antigua, sustituimos la línea naranja por los puntos */
  setTimeout(function(){
    try{
      if(typeof recorridoPuntos!=="undefined" && recorridoPuntos.length) window.dibujarRecorridoGuardado();
    }catch(e){}
  },250);
})();
