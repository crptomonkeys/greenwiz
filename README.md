# greenwiz
The Green Wizard is a discord NFT tipbot launched in 2019. To my knowledge, it is the first ever NFT tipbot on any platform. It was built for cryptomonKeys, and has given out more than 50,000 free NFTs to date. It also has advanced auto-moderation capabilities, and has automatically banned tens of thousands of spammers/scammers.

![Tests](https://github.com/crptomonkeys/greenwiz/actions/workflows/tests.yml/badge.svg)

# To run:
The Green wizard requires python >=3.9 and a redis server. You can configure redis settings, bot private key, etc in settings.py or through the environment variables referenced in that file. Once configured:
```
pip install -r requirements.txt
py bot.py
```

# Contribution:
Contributions are welcome. At this time there is no formal PR format. Please lint with python black and clearly explain your changes in your pull request.

# Uage:
You are welcome to fork the project and use it for your own purposes. Please note that it is licensed under the AGPL (GNU Affero General Public License) which requires you to publicly share any modifications you make to this code if you are running it to provide a service over a network (IE as discord bot). You can edit the github share link in the About command to link to your public repository to fulfill this usage requirement.
