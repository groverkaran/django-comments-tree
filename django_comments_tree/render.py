import json

from draftjs_exporter import html as htmlexporter
from draftjs_exporter.constants import BLOCK_TYPES, ENTITY_TYPES
from draftjs_exporter.defaults import BLOCK_MAP
from draftjs_exporter.dom import DOM
from django.utils.html import escape, linebreaks, urlize


def image(props):
    """
    Components are simple functions that take `props` as parameter and return DOM elements.
    This component creates an image element, with the relevant attributes.

    :param props:
    :return:
    """
    return DOM.create_element('img', {
        'src': props.get('src'),
        'width': props.get('width'),
        'height': props.get('height'),
        'alt': props.get('alt'),
    })


def blockquote(props):
    """
    This component uses block data to render a blockquote.
    :param props:
    :return:
    """
    block_data = props['block']['data']

    # Here, we want to display the block's content so we pass the
    # `children` prop as the last parameter.
    return DOM.create_element('blockquote', {
        'cite': block_data.get('cite')
    }, props['children'])


# https://github.com/springload/draftjs_exporter#configuration
# custom configuration

_config = {
    'block_map': dict(BLOCK_MAP, **{
        BLOCK_TYPES.BLOCKQUOTE: blockquote,
        # BLOCK_TYPES.ATOMIC: {'start': '', 'end': ''},
    }),
    'entity_decorators': {
        # ENTITY_TYPES.LINK: 'link',
        ENTITY_TYPES.IMAGE: image,
        ENTITY_TYPES.HORIZONTAL_RULE: lambda props: DOM.create_element('hr'),
    }
}


def render_draftjs(content_data):
    try:
        cstate = json.loads(content_data)
    except json.JSONDecodeError:
        # invalid json data
        # Should log something...
        return ''
    renderer = htmlexporter.HTML(_config)
    html = renderer.render(cstate)
    return html


def render_plain(content_data):
    return linebreaks(urlize(escape(content_data)))
