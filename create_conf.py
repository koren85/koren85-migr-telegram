#!/usr/bin/python3

#lst=['migr-lenin.vlad:50432','migr-frunz.vlad:56432','migr-kamesh.vlad:52432','migr-vyaznik.vlad:51432','migr-petush.vlad:53432','migr-raduzh.vlad:54432','migr-sobinka.vlad:55432']

dct={'Ленинский район'	:'10.3.0.125:50432','Октябрьский район'	:'10.3.0.125:49432','Фрунзенский район'	:'10.3.0.125:56432',
'Суздальский район'	:'10.3.0.125:48432','Камешковский район'	:'10.3.0.125:52432','Александровский район'	:'10.3.0.125:57432',
'Вязниковский район'	:'10.3.0.125:51432','Гороховецкий район'	:'10.3.0.125:58432','Гусь-Хрустальный'	:'10.3.0.125:59432',
'Киржачский район'	:'10.3.0.125:60432','Ковр и Ковровский район'	:'10.3.0.125:61432','Кольчугинский район'	:'10.3.0.125:62432',
'Меленковскиё район'	:'10.3.0.125:63432','Муром и Муромский район'	:'10.3.0.125:64432','Петушинский район'	:'10.3.0.125:53432',
'ЗАТО город Радужный'	:'10.3.0.125:54432','Селивановский район'	:'10.3.0.125:65432','Собинский район'	:'10.3.0.125:55432',
'Судогодский район'	:'10.3.0.125:47432','Юрьев-Польский район'	:'10.3.0.125:46432','База пенсий госслужащих'	:'10.3.0.125:45432'}

for x,y in dct.items():
   print(f'''
  - name: "{x}"
    driver: "org.postgresql.Driver"
    url: "jdbc:postgresql://{y}/sdu_20250624_121652"
    username: "tomcat"
    password: "password"
    jar_path: "/app/lib/postgresql.jar"
    tables:
      - name: "{x} 3 задача"
        sql_query: "SELECT a_status FROM BDM_FILE_TASK bdm3 JOIN cms_task t ON t.ouid=bdm3.ouid LIMIT 1"
        check_interval: 30  # seconds

      - name: "{x} 1 задача"
        sql_query: "SELECT a_status FROM BDM_STRUCTURE_TASK bdm1 JOIN cms_task t ON t.ouid=bdm1.ouid LIMIT 1"
        check_interval: 5  # seconds

      - name: "{x} 2 задача"
        sql_query: "SELECT a_status FROM BDM_TASK bdm2 JOIN cms_task t ON t.ouid=bdm2.ouid LIMIT 1"
        check_interval: 10  # seconds
'''
)
