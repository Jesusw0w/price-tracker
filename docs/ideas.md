* Lambda scheduled job to highligth products with no price updates - sometimes urls broke or change on Amz side, or even the product was discontinued / not being sold anymore, could be good to have a tracker for this running scheduled everyday
* Turn local scraper into a microservice


Possible endpoints:
* Trackers -> list, get, create, update target price, deactivate
* Prices -> history, summary (lowest/highest/current/change), batch ingest (scraper token)
* Refresh -> create (cooldown), workers
