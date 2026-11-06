'use strict';
const HibamaVisual = (() => {
  function validatePalette(palette) {
    const fail = detail => {throw new Error('Paleta visual inválida em data/ambiental/paleta.json: '+detail);};
    const object = value => value && typeof value==='object' && !Array.isArray(value);
    const color = value => typeof value==='string' && /^#[\da-f]{6}$/i.test(value);
    const dash = value => value==null || typeof value==='string' && /^[\d. ,]*$/.test(value);
    if(!object(palette)||palette.version!==1)fail('versão não suportada.');
    const municipalities=palette.municipalities;
    if(!object(municipalities)||!['color','selectedColor','hoverColor'].every(k=>color(municipalities[k]))||!Array.isArray(municipalities.countScale)||municipalities.countScale.length!==6||!municipalities.countScale.every(color))fail('cores dos municípios ausentes ou inválidas.');
    if(!object(palette.cars)||Object.keys(palette.cars).length!==4||!['AT','PE','SU','CA'].every(k=>object(palette.cars[k])&&color(palette.cars[k].color)&&dash(palette.cars[k].dashArray))||new Set(Object.values(palette.cars).map(s=>s.color.toLowerCase())).size!==4)fail('situações CAR ausentes ou com cores repetidas.');
    if(!object(palette.carSelection)||!color(palette.carSelection.color)||!color(palette.carSelection.hoverColor))fail('destaque CAR inválido.');
    if(!object(palette.layers)||Object.keys(palette.layers).length!==6)fail('camadas ausentes ou inválidas.');
    const modes={ti:'outline',anm:'outline',embargos:'outline',prodes:'event',deter:'event',focos:'point'},colors=[];
    for(const [id,mode] of Object.entries(modes)){
      const spec=palette.layers[id],style=spec?.style;
      if(!object(spec)||!color(spec.color)||!object(style)||style.mode!==mode||!Number.isFinite(style.weight)||style.weight<=0||!Number.isFinite(style.fillOpacity)||style.fillOpacity<0||style.fillOpacity>1||!dash(style.dashArray))fail('estilo da camada '+id+'.');
      if(mode==='outline'&&style.fillOpacity!==0||mode!=='outline'&&style.fillOpacity===0||mode==='point'&&(!Number.isFinite(style.radius)||style.radius<=0))fail('preenchimento ou raio da camada '+id+'.');
      colors.push(spec.color.toLowerCase());
      if(id==='deter'){
        if(!object(style.categories)||!Object.keys(style.categories).length)fail('classes DETER ausentes.');
        for(const category of Object.values(style.categories)){
          if(!object(category)||!color(category.color)||typeof category.label!=='string'||!category.label.trim()||!dash(category.dashArray))fail('classe DETER inválida.');
          if(category.fillOpacity!==undefined||category.weight!==undefined)fail('classes DETER devem herdar preenchimento e espessura.');
          colors.push(category.color.toLowerCase());
        }
      }
    }
    if(new Set(Object.keys(modes).map(id=>palette.layers[id].color.toLowerCase())).size!==6)fail('cada camada precisa de uma cor própria.');
    if(colors.includes(municipalities.selectedColor.toLowerCase()))fail('município selecionado usa cor de camada ambiental.');
    if(!object(palette.method)||typeof palette.method.note!=='string')fail('método ausente.');
    return palette;
  }
  function bindCatalog(catalog,palette){
    validatePalette(palette);
    if(!Array.isArray(catalog?.layers)||catalog.layers.length!==6||new Set(catalog.layers.map(spec=>spec.id)).size!==6||catalog.layers.some(spec=>!Object.hasOwn(palette.layers,spec.id)))throw new Error('Catálogo ambiental incompatível com paleta.json.');
    return {...catalog,layers:catalog.layers.map(spec=>({...spec,...palette.layers[spec.id]}))};
  }
  function environmentalStyle(spec, feature, opacity) {
    const base = spec.style;
    const category = base.categories?.[feature.properties.category];
    const style = {...base, ...(category || {})};
    return {
      color: category?.color || spec.color,
      fillColor: category?.color || spec.color,
      weight: style.weight,
      dashArray: style.dashArray || null,
      opacity,
      fillOpacity: style.fillOpacity * opacity,
      radius: style.radius,
      pane: 'environmental-' + base.mode
    };
  }
  function countyStyle(palette, selected, colored, fillColor, hovered = false) {
    const colors=palette.municipalities;
    return {color: hovered ? colors.hoverColor : selected ? colors.selectedColor : colors.color,
      weight: hovered ? (selected ? 4 : 2.5) : selected ? 3 : 1.5,
      opacity: 1, fill: true, fillColor, fillOpacity: colored ? .32 : 0};
  }
  function carStyle(palette, status, hovered = false) {
    const style=palette.cars[status]||palette.cars.CA;
    return {color: hovered ? palette.carSelection.hoverColor : style.color, dashArray:style.dashArray||null, weight: hovered ? 2.5 : .8,
      opacity: 1, fill: true, fillOpacity: hovered ? .12 : 0};
  }
  return {validatePalette, bindCatalog, environmentalStyle, countyStyle, carStyle};
})();
if (typeof module !== 'undefined') module.exports = HibamaVisual;
