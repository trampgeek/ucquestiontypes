"""Dummy docstring for a function"""
def limited_string(string, max_len):
    """ Takes a string parameter and returns that string truncated if necessary
        to fit in a maximum field width of max_len.
        If the string is more than max_len characters long
        returns the first (max_len - 3) characters of s with '...' appended.
        Otherwise the whole string is returned.
    """
    if len(string) > max_len:
        string = string[:max_len-3] + '...'
    return string


def regions_from_sites(site_info):
    """ Takes a dictionary that maps from site_ids to (site_name, site_region) tuples
    and returns a dictionary where the keys are region name string and the values
    are lists of site_ids in those regions.
    The site names should appear in the same order as they do in the site_info dictionary.
    """
    result = dict()
    for site_id, info in site_info.items():
        name, region = info
        if region in result:
            result[region].append(site_id)
        else:
            result[region] = [site_id]
    return result


def print_region_summary(site_info, region_info):
    """ Prints out the info about sites in each region.
    Regions should be sorted alphabetially by region name string
    whereas sites should be sorted by site_id"""
    for region in sorted(region_info.keys()):
        print(region)
        site_id_list = region_info[region]
        for site_id in sorted(site_id_list):
            name, region = site_info[site_id]
            name = limited_string(name, 40)
            print(f'{site_id:8}:  {name:50}')
