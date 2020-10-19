from urllib.parse import urlparse, parse_qs, ParseResult, urlencode


def url_parser(url, params=None):
    parsed_url = urlparse(url)
    query = parse_qs(parsed_url.query)
    if params is not None and isinstance(params, dict):
        query.update(params)
    encoded_get_args = urlencode(query, doseq=True)

    new_url = ParseResult(
        parsed_url.scheme, parsed_url.netloc, parsed_url.path,
        parsed_url.params, encoded_get_args, parsed_url.fragment
    )
    return new_url.geturl()
