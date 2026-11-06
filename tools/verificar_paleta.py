"""Matrizes de Machado, Oliveira e Fernandes (2009), severidade 1.

https://www.inf.ufrgs.br/~oliveira/pubs_files/CVD_Simulation/CVD_Simulation.html
Confere um fundo de referência; não garante contraste sobre qualquer imagem.
"""
from pathlib import Path
import argparse, json, html
from paleta import load_palette

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description='Confere contraste e gera amostras da paleta ambiental.')
parser.add_argument('--saida', type=Path, help='Pasta opcional das amostras e métricas.')
out = parser.parse_args().saida
try:palette = load_palette()
except ValueError as error:parser.error(str(error))
names={'ti':'Terras Indigenas','anm':'Processos minerarios','embargos':'Areas embargadas','prodes':'Supressao PRODES','deter':'Alertas DETER','focos':'Focos de calor'}
catalog = {'layers':[{'id':name,'name':names[name],**spec} for name,spec in palette['layers'].items()]}
matrices = {
    'Visão de referência': ((1,0,0),(0,1,0),(0,0,1)),
    'Protanopia': ((.152286,1.052583,-.204868),(.114503,.786281,.099216),(-.003882,-.048116,1.051998)),
    'Deuteranopia': ((.367322,.860646,-.227968),(.280085,.672501,.047413),(-.011820,.042940,.968881)),
    'Tritanopia (aprox.)': ((1.255528,-.076749,-.178779),(-.078411,.930809,.147602),(.004733,.691367,.303900)),
}
def rgb(value): return [int(value[i:i+2],16)/255 for i in (1,3,5)]
def linear(value): return value/12.92 if value<=.04045 else ((value+.055)/1.055)**2.4
def encoded(value):
    value=max(0,min(1,value))
    return 12.92*value if value<=.0031308 else 1.055*value**(1/2.4)-.055
def simulate(color,matrix):
    values=list(map(linear,color))
    return [encoded(sum(a*b for a,b in zip(row,values))) for row in matrix]
def hexcolor(color): return '#'+''.join(f'{round(v*255):02x}' for v in color)
def blend(color,bg,alpha): return [a*alpha+b*(1-alpha) for a,b in zip(color,bg)]
def luminance(color): return sum(a*b for a,b in zip((.2126,.7152,.0722),map(linear,color)))
def contrast(a,b):
    v=sorted([luminance(a),luminance(b)])
    return (v[1]+.05)/(v[0]+.05)
rows=[]
for spec in catalog['layers']:
    if spec['id']=='deter':
        for key,style in spec['style']['categories'].items():
            rows.append((style['label'],style['color'],dict(spec['style'],**style)))
    else: rows.append((spec['name'],spec['color'],spec['style']))
for status,label in [('AT','Ativo'),('PE','Pendente'),('SU','Suspenso'),('CA','Cancelado')]:
    spec=palette['cars'][status]
    rows.append(('CAR '+label,spec['color'],{'mode':'outline','fillOpacity':0,'dashArray':spec.get('dashArray',''),'sampleOpacity':1}))
rows.append(('Municipio selecionado',palette['municipalities']['selectedColor'],{'mode':'outline','fillOpacity':0,'sampleOpacity':1}))
rows.append(('CAR selecionado',palette['carSelection']['color'],{'mode':'outline','fillOpacity':0,'sampleOpacity':1}))
height=108+len(rows)*48+110
bg=rgb('#203d31')
svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="1240" height="{height}" viewBox="0 0 1240 {height}">', '<rect width="1240" height="100%" fill="#fafbf7"/>', '<style>text{font-family:Arial,sans-serif;fill:#193e35;font-size:13px}</style>', '<text x="24" y="30" style="font-size:21px">Hibama · conferência da paleta ambiental</text>', '<text x="24" y="55">Ambiental 65%, CAR e selecao 100%; fundo verde escuro #203d31; cores combinadas com contornos, tracejados e rótulos.</text>']
results=[]
for column,(name,matrix) in enumerate(matrices.items()):
    x=320+column*224
    svg.append(f'<text x="{x}" y="90">{name}</text>')
    background=simulate(bg,matrix)
    for row,(label,color,style) in enumerate(rows):
        y=108+row*48
        if column==0:svg.append(f'<text x="24" y="{y+26}">{html.escape(label)}</text>')
        alpha=style.get('sampleOpacity',.65)
        stroke=simulate(blend(rgb(color),bg,alpha),matrix)
        fill=simulate(blend(rgb(color),bg,alpha*style['fillOpacity']),matrix)
        dash=style.get('dashArray','')
        svg.append(f'<rect x="{x}" y="{y}" width="204" height="38" rx="3" fill="{hexcolor(background)}"/>')
        if style['mode']=='point':
            svg.append(f'<circle cx="{x+100}" cy="{y+19}" r="5" fill="{hexcolor(fill)}" stroke="{hexcolor(stroke)}"/>')
        else:
            svg.append(f'<rect x="{x+14}" y="{y+8}" width="175" height="22" fill="{hexcolor(fill)}" stroke="{hexcolor(stroke)}" stroke-width="2" stroke-dasharray="{dash}"/>')
        results.append(dict(simulation=name,label=label,opacity=alpha,stroke_contrast=round(contrast(stroke,background),2)))
svg+=[f'<text x="24" y="{height-80}">Modelo: Machado, Oliveira e Fernandes (2009), matrizes na severidade 1, em RGB linear, com recorte ao gamut.</text>', f'<text x="24" y="{height-56}">Simulação é uma aproximação. Algumas cores se aproximam: a identificação usa também padrões e rótulos.</text>', f'<text x="24" y="{height-32}">A conferência no satélite real está nas capturas dos três municípios. Não há garantia para todo fundo ou usuário.</text>', '</svg>']
if out:
    out.mkdir(parents=True,exist_ok=True)
    (out/'paleta-validacao.svg').write_text('\n'.join(svg),encoding='utf-8')
    (out/'paleta-metricas.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
print(f'Paleta: {len(rows)} simbolos, quatro condicoes visuais; simulacao em RGB linear concluida.')
print('Contraste minimo no fundo de referencia (ambiental 65%, CAR e selecao 100%):',min(r['stroke_contrast'] for r in results))
assert all(r['stroke_contrast']>=3 for r in results), 'Contraste abaixo de 3:1 no fundo de referência.'
