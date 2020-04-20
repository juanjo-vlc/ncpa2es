# DISCLAIMER: NOT READY FOR PRODUCTION USE
# ncpa2es

Read Nagios Cross-Platform Agent metrics and store them on an Elasticsearch Cluster. Then use Grafana to plot some graphs on a modest dashboard.

Sometimes you are working on an environment with a limited set of tools available, but if you have an Elasticsearch cluster at hand, and NCPA installed, maybe because your customer asked for it, now you have the possibility to plot some metrics on a grafana dashboard.

Storing metrics on ES may only require a few megabytes a day if your have only a few hosts, and, you can tweak the script to exclude some metrics if you don't need them and want to save a few bytes.

## Getting Started

1. Copy ncpa2es.py and config.yml-dist to someplace on a system capable of reaching ncpa_listener on your hosts and your ES cluster.
2. Grab a copy [check_ncpa.py](https://github.com/NagiosEnterprises/ncpa/tree/master/client) and put it on the same place.
3. Rename config.yml-dist to config.yml and tailor it to match your setup
4. Rut ncpa2es.py at regular intervals, for instance, using cron.


## Plotting in Grafana

If you don't have a working copy of grafana, you can visit their [getting started](https://grafana.com/docs/grafana/latest/guides/getting_started/) page.

Once you have a working grafana be sure your grafana server is able to access your ES cluster, it doesn't matter if it can be accessed directly or using a SSH tunnel, or querying through your browser.

### Set up your datasource:

This is an example datasource, set it up to match your ES. The **index name** template should match the index defined in config.yml file.

![alt text](./resources/datasource.png "datasource setup"
)

It's not necessary to use the same user defined in config.yml, and it's considered a best practice to use different users for writing (ncpa2es.py) and reading (grafana).

### Import the dashboard

Import the dashboard on grafana using the wizard and choose the previously configured datasource, and you are ready to go.

### Have fun!

Yes, have fun!.

Now you can play with the panels, the querys, set up alerts and so on. And when you get bored, I will be here to read your complaints, you know what to do.

## Tweaks

### Use a template to define the number of shards and other stuff for your .ncpa-metrics indexes.

```
{
  "order": 0,
  "template": ".ncpa-metrics-*",
  "settings": {
    "index": {
      "number_of_shards": "2",
      "number_of_replicas": "1"
    }
  },
  "mappings": {},
  "aliases": {}
}
```
I'm working with automatic id generation and automatic mapping, so this is the only settings I've used.

### Index lifecycle manament

You can use the [Elasticsearch X-Pack ILM](https://www.elastic.co/guide/en/elasticsearch/reference/current/getting-started-index-lifecycle-management.html) to manage the lifcycle of indices. (Recommeded)

You can also use [Elasticsearch Curator](https://www.elastic.co/guide/en/elasticsearch/client/curator/current/index.html) if you don't have a licensed X-Pack.

Another option is to use the [Elasticsearch Index API](https://www.elastic.co/guide/en/elasticsearch/reference/current/indices-delete-index.html) to delete old indices.

And of course, you can keep them forever.


## References

* [NagiosEnterprises / ncpa](https://github.com/NagiosEnterprises/ncpa/tree/master/client) - My reference for extracting ncpa data.
* [trevorndodds / elasticsearch-metrics](https://github.com/trevorndodds/elasticsearch-metrics) - My inspiration for the whole work.


## Authors

* **Juanjo García** - *Initial work* - [juanjo-vlc](https://github.com/juanjo-vlc)

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details

## Next steps
- [ ] Remove dependency from ncpa
- [ ] Manage ncpa host failure
- [ ] Manage es host failure
- [X] Upload to github
- [ ] Convert to a long running process/systemd service
- [ ] Reload by signal
- [ ] Improve documentation *(endless loop)*
