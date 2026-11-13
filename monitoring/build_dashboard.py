"""Generate the versioned Grafana dashboard for the synthetic HTTP monitor."""
import json
from pathlib import Path

FILTER = '{service_name="ihospitalutility-monitor"}'
FRESH = f'(time() - max(ihospital_probe_last_run_timestamp_seconds{FILTER}) < 180)'

def metric(expr):
    return f'({expr}) and on() {FRESH}'

def panel(i, title, expr, x, y, w=6, h=5, unit='short', kind='stat'):
    return {
        'id': i, 'title': title, 'type': kind,
        'gridPos': {'x': x, 'y': y, 'w': w, 'h': h},
        'datasource': {'type': 'prometheus', 'uid': 'prometheus'},
        'targets': [{'refId': 'A', 'expr': expr, 'legendFormat': '{{check}}', 'instant': kind == 'stat', 'range': kind != 'stat'}],
        'fieldConfig': {'defaults': {'unit': unit, 'noValue': 'Sem telemetria', 'color': {'mode': 'thresholds'}, 'thresholds': {'mode': 'absolute', 'steps': [{'color':'green','value':None}]}}, 'overrides': []},
        'options': {'reduceOptions': {'values':False,'calcs':['lastNotNull'],'fields':''}, 'orientation':'auto', 'textMode':'auto', 'colorMode':'value', 'graphMode':'none'} if kind=='stat' else {'legend':{'displayMode':'list','placement':'bottom'},'tooltip':{'mode':'multi'}}
    }

panels = [{
    'id': 1, 'title': 'Cobertura e leitura', 'type': 'text',
    'gridPos': {'x':0,'y':0,'w':24,'h':9},
    'options': {'mode':'markdown', 'content': '**HTTPS a cada 60 s.** Página, Blazor, PWA e certificado.\n\n**Falha com HTTP 200?** O conteúdo também é validado.\n\nColeta ausente ou antiga não confirma saúde.'}
}]
p = panel(2, 'Disponibilidade agora', metric('min(ihospital_probe_success'+FILTER+')'),0,5)
p['fieldConfig']['defaults']['mappings'] = [{'type':'value','options':{'0':{'text':'Falha','color':'red'},'1':{'text':'OK','color':'green'}}}]
p['fieldConfig']['defaults']['thresholds']['steps']=[{'color':'red','value':None},{'color':'green','value':1}]
panels.append(p)
panels.append(panel(3,'Resposta · página inicial',metric('max(ihospital_probe_duration_seconds{service_name="ihospitalutility-monitor",check="home"})'),6,5,unit='s'))
panels.append(panel(4,'Certificado · validade',metric('(max(ihospital_probe_tls_cert_expiry_timestamp_seconds'+FILTER+' > 0) - time()) / 86400'),12,5,unit='d'))
panels[-1]['fieldConfig']['defaults']['thresholds']['steps']=[{'color':'red','value':None},{'color':'orange','value':7},{'color':'green','value':21}]
panels.append(panel(5,'Última coleta · idade','time() - max(ihospital_probe_last_run_timestamp_seconds'+FILTER+')',18,5,unit='s'))
panels[-1]['fieldConfig']['defaults']['thresholds']['steps']=[{'color':'green','value':None},{'color':'orange','value':120},{'color':'red','value':180}]
panels.append(panel(6,'Disponibilidade · período','100 * avg_over_time(ihospital_probe_success'+FILTER+'[$__range])',0,10,w=12,unit='percent'))
panels.append(panel(7,'HTTP · por verificação',metric('ihospital_probe_http_status_code'+FILTER),12,10,w=12))
panels.append(panel(8,'Tempo de resposta · histórico','ihospital_probe_duration_seconds'+FILTER,0,15,w=12,h=8,kind='timeseries',unit='s'))
panels.append(panel(9,'Disponibilidade · histórico','ihospital_probe_success'+FILTER,12,15,w=12,h=8,kind='timeseries',unit='short'))
panels[-1]['fieldConfig']['defaults']['min']=0
panels[-1]['fieldConfig']['defaults']['max']=1
panels.append({
    'id':10,'title':'Registros das verificações · não são acessos de usuários','type':'logs',
    'gridPos':{'x':0,'y':23,'w':24,'h':10},
    'datasource':{'type':'loki','uid':'loki'},
    'targets':[{'refId':'A','expr':'{service_name="ihospitalutility-monitor"}','queryType':'range','maxLines':100}],
    'options':{'showTime':True,'showLabels':False,'wrapLogMessage':True,'sortOrder':'Descending','dedupStrategy':'none','enableLogDetails':True}
})
for item in panels[1:]:
    item['gridPos']['y'] += 4
panels.append({
    'id':11, 'title':'Limites e retenção', 'type':'text',
    'gridPos':{'x':0,'y':37,'w':24,'h':12},
    'options':{'mode':'markdown','content':'**Limites:** sondas deste servidor, não acessos de usuários. Sem dados clínicos, cálculos, erros JavaScript ou validação de uso offline.\n\n**Histórico desde ativação:** métricas até **7 dias** e 1 GB compartilhado; logs até **72 horas**.\n\nSem alertas de notificação.'}
})
board={'uid':'ihospitalutility-overview','title':'iHospitalUtility · Visão geral','tags':['iHospitalUtility','monitoramento-sintetico'],'schemaVersion':40,'version':1,'timezone':'browser','refresh':'1m','time':{'from':'now-1h','to':'now'},'editable':True,'panels':panels,'links':[{'title':'Abrir aplicação','type':'link','url':'https://ihospitalutility.allandeba.dev.br','targetBlank':True}],'templating':{'list':[]},'annotations':{'list':[]}}
if __name__=='__main__':
    Path(__file__).with_name('dashboard.json').write_text(json.dumps(board,ensure_ascii=False,indent=2)+'\n')
