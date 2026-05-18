# Catàleg de fonts OSINT normalitzat

Font original: https://raw.githubusercontent.com/OldBonhart/Osint-Resources/master/README.md

## Normalització

Format: font, tipus, cobertura, accés, cost, quota, freqüència.
Scoring: fiabilitat, cobertura, latència, cost, accessibilitat (1-5).

Total de fonts: 119

> **Nota de revisió (EINA):** S'han exclòs del Top 20 fonts amb risc legal/reputacional
> (doxxing, SSN lookup, VK scraping, filtracions). Preferir fonts integrades a la plataforma.

## Top 20 global (revisat per ús professional)

| # | Font | Categoria | Score | URL |
| --- | --- | --- | --- | --- |
| 1 | GDELT | geopolitica | 5.0 | Integrat EINA `/api/osint/gdelt` |
| 2 | OpenSanctions | geopolitica | 5.0 | Integrat EINA `/api/osint/opensanctions` |
| 3 | CFR / IISS / Brookings (RSS) | geopolitica | 4.8 | Integrat EINA `/api/osint/rss` |
| 4 | censys.io | dominis_i_infra | 4.4 | https://censys.io/ |
| 5 | www.shodan.io | dominis_i_infra | 4.4 | Integrat EINA `/api/osint/shodan` |
| 6 | whois.icann.org | dominis_i_infra | 4.4 | https://whois.icann.org/en |
| 7 | Google News | notícies | 4.3 | Integrat EINA `/api/osint/google-news` |
| 8 | Reddit | notícies | 4.2 | Integrat EINA `/api/osint/reddit` |
| 9 | GitHub | infraestructura | 4.2 | Integrat EINA `/api/osint/github` |
| 10 | Wayback Machine | infraestructura | 4.2 | Integrat EINA `/api/osint/wayback` |
| 11 | www.marinetraffic.com | geolocalitzacio | 4.0 | https://www.marinetraffic.com |
| 12 | 29a.ch (photo forensics) | imatges | 3.8 | https://29a.ch/photo-forensics/ |
| 13 | berify.com | imatges | 3.8 | https://berify.com/ |
| 14 | fotoforensics.com | imatges | 3.8 | http://fotoforensics.com/ |
| 15 | checkusernames.com | altres | 3.8 | https://checkusernames.com |
| 16 | whatismyipaddress.com | dominis_i_infra | 4.0 | https://whatismyipaddress.com |
| 17 | whois.domaintools.com | dominis_i_infra | 4.0 | http://whois.domaintools.com/ |
| 18 | ipstack | geolocalitzacio | 4.0 | Integrat EINA `/api/osint/ip-geolocation` |
| 19 | Foreign Affairs (RSS) | geopolitica | 4.5 | Integrat EINA RSS |
| 20 | International Crisis Group | geopolitica | 4.5 | Integrat EINA RSS |

## Top 20 global (catàleg original — conté fonts excloses)

| # | Font | Categoria | Score | URL |
| --- | --- | --- | --- | --- |
| 1 | censys.io | dominis_i_infra | 4.4 | https://censys.io/ |
| 2 | findmevk.com | socials | 4.4 | https://findmevk.com/ |
| 3 | pipl.com | dominis_i_infra | 4.4 | https://pipl.com/ |
| 4 | siph0n.in | dominis_i_infra | 4.4 | http://siph0n.in/leaks.php |
| 5 | SSN(номер соц. страхования граждан USA | socials | 4.4 | https://www.docusearch.com/find-a-social-security-number.html |
| 6 | vk.watch | socials | 4.4 | https://vk.watch/ |
| 7 | whatismyipaddress.com | dominis_i_infra | 4.4 | https://whatismyipaddress.com |
| 8 | whois.domaintools.com | dominis_i_infra | 4.4 | http://whois.domaintools.com/ |
| 9 | whois.icann.org | dominis_i_infra | 4.4 | https://whois.icann.org/en |
| 10 | www.ipaddresslocation.org | dominis_i_infra | 4.4 | http://www.ipaddresslocation.org/ |
| 11 | www.shodan.io | dominis_i_infra | 4.4 | https://www.shodan.io/ |
| 12 | Анализ лайков соц. сети VK | socials | 4.4 | http://searchlikes.ru/login |
| 13 | Архив запросов,поиск цифровых отпечатков пользователей сервиса whois | dominis_i_infra | 4.4 | https://whoisology.com/ |
| 14 | Поиск фото по геометкам в соц. сетях | socials | 4.4 | http://sanstv.ru/photomap/ |
| 15 | seatracker.ru | geolocalitzacio | 4.0 | https://seatracker.ru/ais.php |
| 16 | www.marinetraffic.com | geolocalitzacio | 4.0 | https://www.marinetraffic.com |
| 17 | 29a.ch | altres | 3.8 | https://29a.ch/photo-forensics/#level-sweep |
| 18 | berify.com | imatges | 3.8 | https://berify.com/ |
| 19 | betaface.com | imatges | 3.8 | http://betaface.com/demo_old.html |
| 20 | checkusernames.com | altres | 3.8 | https://checkusernames.com |

## Top 5 per categoria

### dominis_i_infra

| # | Font | Score | URL |
| --- | --- | --- | --- |
| 1 | censys.io | 4.4 | https://censys.io/ |
| 2 | pipl.com | 4.4 | https://pipl.com/ |
| 3 | siph0n.in | 4.4 | http://siph0n.in/leaks.php |
| 4 | whatismyipaddress.com | 4.4 | https://whatismyipaddress.com |
| 5 | whois.domaintools.com | 4.4 | http://whois.domaintools.com/ |

### socials

| # | Font | Score | URL |
| --- | --- | --- | --- |
| 1 | findmevk.com | 4.4 | https://findmevk.com/ |
| 2 | SSN(номер соц. страхования граждан USA | 4.4 | https://www.docusearch.com/find-a-social-security-number.html |
| 3 | vk.watch | 4.4 | https://vk.watch/ |
| 4 | Анализ лайков соц. сети VK | 4.4 | http://searchlikes.ru/login |
| 5 | Поиск фото по геометкам в соц. сетях | 4.4 | http://sanstv.ru/photomap/ |

### geolocalitzacio

| # | Font | Score | URL |
| --- | --- | --- | --- |
| 1 | seatracker.ru | 4.0 | https://seatracker.ru/ais.php |
| 2 | www.marinetraffic.com | 4.0 | https://www.marinetraffic.com |

### altres

| # | Font | Score | URL |
| --- | --- | --- | --- |
| 1 | 29a.ch | 3.8 | https://29a.ch/photo-forensics/#level-sweep |
| 2 | checkusernames.com | 3.8 | https://checkusernames.com |
| 3 | ciberpatrulla.com | 3.8 | https://ciberpatrulla.com/links/ |
| 4 | danwin1210.me | 3.8 | https://danwin1210.me/uploads/ |
| 5 | databases.today | 3.8 | http://databases.today/ |

### imatges

| # | Font | Score | URL |
| --- | --- | --- | --- |
| 1 | berify.com | 3.8 | https://berify.com/ |
| 2 | betaface.com | 3.8 | http://betaface.com/demo_old.html |
| 3 | fotoforensics.com | 3.8 | http://fotoforensics.com/ |
| 4 | karmadecay.com | 3.8 | http://karmadecay.com/r/maledom |
| 5 | pimeyes.com | 3.8 | https://pimeyes.com/en/ |

### emails_i_telefon

| # | Font | Score | URL |
| --- | --- | --- | --- |
| 1 | hacked-emails.com | 3.8 | https://hacked-emails.com/ |
| 2 | Телефонный справочник городов СНГ | 3.8 | http://nomer-org.me/ |

### registres_publics

| # | Font | Score | URL |
| --- | --- | --- | --- |
| 1 | publicdbhost.dmca.gripe | 3.8 | http://publicdbhost.dmca.gripe/ |
| 2 | publicrecords.searchsystems.net | 3.8 | http://publicrecords.searchsystems.net/ |

