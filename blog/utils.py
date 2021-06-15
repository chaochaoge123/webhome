from bs4 import BeautifulSoup


def trans_dict_to_xml(data_dict):
    """
    json -> xml
    :param data_dict: json 格式数据
    :return: xml 格式数据
    """
    data_xml = []
    for k in sorted(data_dict.keys()):
        v = data_dict.get(k)
        if k == 'detail' and not v.startswith('<![CDATA['):
            v = '<![CDATA[{}]]>'.format(v)
        data_xml.append('<{key}>{value}</{key}>'.format(key=k, value=v))
    return '<xml>{}</xml>'.format(''.join(data_xml)).encode('utf-8')


def trans_xml_to_dict(data_xml):
    """
    xml -> json
    :param data_xml: xml 格式数据
    :return: json 格式数据
    """
    soup = BeautifulSoup(data_xml, features='xml')
    xml = soup.find('xml')
    if not xml:
        return {}
    data_dict = dict([(item.name, item.text) for item in xml.find_all()])
    return data_dict
