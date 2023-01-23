import requests
import json
import time

# url = "https://wax.eu.eosamsterdam.net:443"
url = "https://api.wax.alohaeos.com:443"
endpoint = "/v2/history/get_actions"

starting_timestamp = "2023-01-19T00:00:00.000"


def get_one(account="dao.worlds", actname="votecust", after=None, limit=1000) -> str:
    composed = f"{url}{endpoint}?account={account}&act.name={actname}&limit={limit}"
    if after is not None:
        composed += f"&after={after}"
    res = requests.get(composed)
    res.raise_for_status()
    result = json.loads(res.content)
    print(result)
    return result


def get_all(starting_timestamp) -> str:
    results = []
    while True:
        try:
            response = get_one(after=starting_timestamp)
            new_actions = [action["act"] for action in response["actions"]]
            results.extend(new_actions)
            last_timestamp = response["actions"][-1]["timestamp"]
        except (IndexError, requests.exceptions.HTTPError):
            return results
        print(
            f"got {len(response['actions'])=} results, {len(results)=} sleeping for 3s..."
        )
        if len(new_actions) < 1000 or len(results) >= 15000:
            return results
        time.sleep(3)
        response = get_one(after=last_timestamp)
    return results


def get_selected():
    response = get_all(starting_timestamp)
    relevants = dict()
    for x in response:
        if x["data"]["voter"] in relevants:  # ignore prior votes
            continue
        if x["data"]["dac_id"] != "nerix":
            continue
        relevants[x["data"]["voter"]] = x["data"]["newvotes"]
    relevants = {
        x["data"]["voter"]: x["data"]["newvotes"]
        for x in response
        if x["data"]["dac_id"] == "nerix"
    }
    print(f"{relevants=}")
    print(f"{len(relevants)=}")
    return relevants


__relevants = {}


def sort_relevants(relevants=None):
    if relevants is None:
        relevants = __relevants
    valid_addresses = []
    voted_both = []
    for key, value in relevants.items():
        if "a52qw.wam" in value and "b52qw.wam" in value:
            voted_both.append(key)
        elif "a52qw.wam" in value or "b52qw.wam" in value:
            valid_addresses.append(key)
    return voted_both, valid_addresses


if __name__ == "__main__":
    rel = get_selected()
    both, valid = sort_relevants(rel)
    both_c = ",".join(x for x in both)
    valid_c = ",".join(x for x in valid)
    print(
        f"The following people voted for both of our candidates since {starting_timestamp}:\n{both_c}"
    )
    print(
        f"The following people voted for one of our candidates but not the other:\n{valid_c}"
    )
    print(f"{len(both)} voted for both.")
    print(f"{len(valid)} voted for one but not the other.")
