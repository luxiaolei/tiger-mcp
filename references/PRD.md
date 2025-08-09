

we use https://github.com/jlowin/fastmcp to build a mcp for tiger broker.

able to support:
1) multipal accounts for trading tools
2) configure a spefic account for data fetching tools
3) api keys auth for different accounts, (api key binds to specific account for trading endpoints)
4) Auto refresh tiger tokens
5) A dashboard displaies (authed by apikey etc or user name pass word) account status etc, and tradings. use thrid party dashabord libs (not sure if grafna suitable?)
6) After implement, needs to tests, and also implement CI/CD

reference and chanllenages:

1) I have had an old project in @references/tiger_dashboard which suecfully can dispalys accoutn status, but it has bugs and uses simple streamnlit, and doesnt support multipal account. Becasue teh tiger api sdk laods its key at fixed apth and seems only 1 at a time.
2) I have downloaded the references/openapi-python-sdk here.