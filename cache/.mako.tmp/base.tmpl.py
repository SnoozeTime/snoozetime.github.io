# -*- coding:utf-8 -*-
from mako import runtime, filters, cache
UNDEFINED = runtime.UNDEFINED
STOP_RENDERING = runtime.STOP_RENDERING
__M_dict_builtin = dict
__M_locals_builtin = locals
_magic_number = 10
_modified_time = 1522919669.3046312
_enable_loop = True
_template_filename = 'themes/readable/templates/base.tmpl'
_template_uri = 'base.tmpl'
_source_encoding = 'utf-8'
_exports = ['sourcelink', 'content', 'belowtitle', 'extra_head']


def _mako_get_namespace(context, name):
    try:
        return context.namespaces[(__name__, name)]
    except KeyError:
        _mako_generate_namespaces(context)
        return context.namespaces[(__name__, name)]
def _mako_generate_namespaces(context):
    ns = runtime.TemplateNamespace('base', context._clean_inheritance_tokens(), templateuri='base_helper.tmpl', callables=None,  calling_uri=_template_uri)
    context.namespaces[(__name__, 'base')] = ns

def render_body(context,**pageargs):
    __M_caller = context.caller_stack._push_frame()
    try:
        __M_locals = __M_dict_builtin(pageargs=pageargs)
        _import_ns = {}
        _mako_get_namespace(context, 'base')._populate(_import_ns, ['*'])
        def extra_head():
            return render_extra_head(context._locals(__M_locals))
        search_form = _import_ns.get('search_form', context.get('search_form', UNDEFINED))
        _link = _import_ns.get('_link', context.get('_link', UNDEFINED))
        blog_url = _import_ns.get('blog_url', context.get('blog_url', UNDEFINED))
        template_hooks = _import_ns.get('template_hooks', context.get('template_hooks', UNDEFINED))
        len = _import_ns.get('len', context.get('len', UNDEFINED))
        def sourcelink():
            return render_sourcelink(context._locals(__M_locals))
        translations = _import_ns.get('translations', context.get('translations', UNDEFINED))
        def content():
            return render_content(context._locals(__M_locals))
        def belowtitle():
            return render_belowtitle(context._locals(__M_locals))
        blog_title = _import_ns.get('blog_title', context.get('blog_title', UNDEFINED))
        set_locale = _import_ns.get('set_locale', context.get('set_locale', UNDEFINED))
        body_end = _import_ns.get('body_end', context.get('body_end', UNDEFINED))
        permalink = _import_ns.get('permalink', context.get('permalink', UNDEFINED))
        content_footer = _import_ns.get('content_footer', context.get('content_footer', UNDEFINED))
        lang = _import_ns.get('lang', context.get('lang', UNDEFINED))
        base = _mako_get_namespace(context, 'base')
        rel_link = _import_ns.get('rel_link', context.get('rel_link', UNDEFINED))
        messages = _import_ns.get('messages', context.get('messages', UNDEFINED))
        navigation_links = _import_ns.get('navigation_links', context.get('navigation_links', UNDEFINED))
        __M_writer = context.writer()
        __M_writer('\n')
        __M_writer(str(set_locale(lang)))
        __M_writer('\n')
        __M_writer(str(base.html_headstart()))
        __M_writer('\n')
        if 'parent' not in context._data or not hasattr(context._data['parent'], 'extra_head'):
            context['self'].extra_head(**pageargs)
        

        __M_writer('\n')
        __M_writer(str(template_hooks['extra_head']()))
        __M_writer('\n</head>\n<body>\n<div class="container" id="container">\n    <!--Body content-->\n    <!--End of body content-->\n    <div>\n    <a href="')
        __M_writer(str(blog_url))
        __M_writer('"><h1>')
        __M_writer(str(blog_title))
        __M_writer('</h1></a>\n    </div>\n    <div id="content">\n        ')
        __M_writer(str(template_hooks['page_header']()))
        __M_writer('\n        ')
        if 'parent' not in context._data or not hasattr(context._data['parent'], 'content'):
            context['self'].content(**pageargs)
        

        __M_writer('\n    </div>\n    <div class="row-fluid">\n        <div class="span6" style="text-align: right; border-right: 2px solid #ccc; padding-right: 20px;">\n            <ul class="unstyled bottom">\n')
        for url, text in navigation_links[lang]:
            if rel_link(permalink, url) == "#":
                __M_writer('                        <li class="active"><a href="')
                __M_writer(str(url))
                __M_writer('">')
                __M_writer(str(text))
                __M_writer('</a>\n')
            else:
                __M_writer('                        <li><a href="')
                __M_writer(str(url))
                __M_writer('">')
                __M_writer(str(text))
                __M_writer('</a>\n')
        __M_writer('                ')
        __M_writer(str(template_hooks['menu']()))
        __M_writer('\n            </ul>\n        </div>\n        <div class="span6" style="margin-left: 20px;">\n            <ul class="unstyled bottom">\n            ')
        if 'parent' not in context._data or not hasattr(context._data['parent'], 'belowtitle'):
            context['self'].belowtitle(**pageargs)
        

        __M_writer('\n            ')
        if 'parent' not in context._data or not hasattr(context._data['parent'], 'sourcelink'):
            context['self'].sourcelink(**pageargs)
        

        __M_writer('\n            <li>Shares: <div id="share"></div></li>\n            </ul>\n            <div>\n')
        if search_form:
            __M_writer('                ')
            __M_writer(str(search_form))
            __M_writer('\n')
        __M_writer('            ')
        __M_writer(str(template_hooks['menu_alt']()))
        __M_writer('\n            </div>\n        </div>\n    </div>\n    <hr>\n    <div class="footer">\n    ')
        __M_writer(str(content_footer))
        __M_writer('\n    ')
        __M_writer(str(template_hooks['page_footer']()))
        __M_writer('\n    </div>\n</div>\n    ')
        __M_writer(str(base.late_load_js()))
        __M_writer('\n    <script type="text/javascript" src="/assets/js/jquery.sharrre-1.3.4.min.js"></script>\n    <script type="text/javascript">\n        jQuery("a.image-reference").colorbox({rel:"gal",maxWidth:"80%",maxHeight:"80%",scalePhotos:true});\n        $(\'#share\').sharrre({\n        share: {\n            googlePlus: true,\n            twitter: true\n        },\n        buttons: {\n            googlePlus: {annotation:\'bubble\'},\n            twitter: {count: \'horizontal\'}\n        },\n        hover: function(api, options){\n            $(api.element).find(\'.buttons\').show();\n        },\n        hide: function(api, options){\n            $(api.element).find(\'.buttons\').hide();\n        },\n        enableTracking: true,\n        urlCurl: ""\n        });\n    </script>\n    ')
        __M_writer(str(body_end))
        __M_writer('\n    ')
        __M_writer(str(template_hooks['body_end']()))
        __M_writer('\n</body>\n')
        return ''
    finally:
        context.caller_stack._pop_frame()


def render_sourcelink(context,**pageargs):
    __M_caller = context.caller_stack._push_frame()
    try:
        _import_ns = {}
        _mako_get_namespace(context, 'base')._populate(_import_ns, ['*'])
        def sourcelink():
            return render_sourcelink(context)
        __M_writer = context.writer()
        __M_writer(' ')
        return ''
    finally:
        context.caller_stack._pop_frame()


def render_content(context,**pageargs):
    __M_caller = context.caller_stack._push_frame()
    try:
        _import_ns = {}
        _mako_get_namespace(context, 'base')._populate(_import_ns, ['*'])
        def content():
            return render_content(context)
        __M_writer = context.writer()
        return ''
    finally:
        context.caller_stack._pop_frame()


def render_belowtitle(context,**pageargs):
    __M_caller = context.caller_stack._push_frame()
    try:
        _import_ns = {}
        _mako_get_namespace(context, 'base')._populate(_import_ns, ['*'])
        messages = _import_ns.get('messages', context.get('messages', UNDEFINED))
        _link = _import_ns.get('_link', context.get('_link', UNDEFINED))
        def belowtitle():
            return render_belowtitle(context)
        permalink = _import_ns.get('permalink', context.get('permalink', UNDEFINED))
        len = _import_ns.get('len', context.get('len', UNDEFINED))
        lang = _import_ns.get('lang', context.get('lang', UNDEFINED))
        rel_link = _import_ns.get('rel_link', context.get('rel_link', UNDEFINED))
        translations = _import_ns.get('translations', context.get('translations', UNDEFINED))
        __M_writer = context.writer()
        __M_writer('\n')
        if len(translations) > 1:
            __M_writer('                    <li>\n')
            for langname in translations.keys():
                if langname != lang:
                    __M_writer('                            <a href="')
                    __M_writer(str(rel_link(permalink, _link("index", None, langname))))
                    __M_writer('">')
                    __M_writer(str(messages[langname]["LANGUAGE"]))
                    __M_writer('</a>\n')
            __M_writer('                    </li>\n')
        __M_writer('            ')
        return ''
    finally:
        context.caller_stack._pop_frame()


def render_extra_head(context,**pageargs):
    __M_caller = context.caller_stack._push_frame()
    try:
        _import_ns = {}
        _mako_get_namespace(context, 'base')._populate(_import_ns, ['*'])
        def extra_head():
            return render_extra_head(context)
        __M_writer = context.writer()
        __M_writer('\n')
        return ''
    finally:
        context.caller_stack._pop_frame()


"""
__M_BEGIN_METADATA
{"source_encoding": "utf-8", "line_map": {"128": 47, "136": 47, "142": 19, "195": 5, "23": 2, "26": 0, "155": 36, "170": 36, "171": 37, "172": 38, "173": 39, "174": 40, "175": 41, "176": 41, "177": 41, "178": 41, "179": 41, "180": 44, "181": 46, "201": 195, "57": 2, "58": 3, "59": 3, "60": 4, "61": 4, "66": 7, "67": 8, "68": 8, "69": 15, "70": 15, "71": 15, "72": 15, "73": 18, "74": 18, "79": 19, "80": 24, "81": 25, "82": 26, "83": 26, "84": 26, "85": 26, "86": 26, "87": 27, "88": 28, "89": 28, "90": 28, "91": 28, "92": 28, "93": 31, "94": 31, "95": 31, "187": 5, "100": 46, "105": 47, "106": 51, "107": 52, "108": 52, "109": 52, "110": 54, "111": 54, "112": 54, "113": 60, "114": 60, "115": 61, "116": 61, "117": 64, "118": 64, "119": 87, "120": 87, "121": 88, "122": 88}, "uri": "base.tmpl", "filename": "themes/readable/templates/base.tmpl"}
__M_END_METADATA
"""
