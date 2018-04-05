# -*- coding:utf-8 -*-
from mako import runtime, filters, cache
UNDEFINED = runtime.UNDEFINED
STOP_RENDERING = runtime.STOP_RENDERING
__M_dict_builtin = dict
__M_locals_builtin = locals
_magic_number = 10
_modified_time = 1522919669.754828
_enable_loop = True
_template_filename = 'themes/readable/templates/index.tmpl'
_template_uri = 'index.tmpl'
_source_encoding = 'utf-8'
_exports = ['content']


def _mako_get_namespace(context, name):
    try:
        return context.namespaces[(__name__, name)]
    except KeyError:
        _mako_generate_namespaces(context)
        return context.namespaces[(__name__, name)]
def _mako_generate_namespaces(context):
    ns = runtime.TemplateNamespace('comments', context._clean_inheritance_tokens(), templateuri='comments_helper.tmpl', callables=None,  calling_uri=_template_uri)
    context.namespaces[(__name__, 'comments')] = ns

    ns = runtime.TemplateNamespace('helper', context._clean_inheritance_tokens(), templateuri='index_helper.tmpl', callables=None,  calling_uri=_template_uri)
    context.namespaces[(__name__, 'helper')] = ns

def _mako_inherit(template, context):
    _mako_generate_namespaces(context)
    return runtime._inherit_from(context, 'base.tmpl', _template_uri)
def render_body(context,**pageargs):
    __M_caller = context.caller_stack._push_frame()
    try:
        __M_locals = __M_dict_builtin(pageargs=pageargs)
        date_format = context.get('date_format', UNDEFINED)
        helper = _mako_get_namespace(context, 'helper')
        messages = context.get('messages', UNDEFINED)
        def content():
            return render_content(context._locals(__M_locals))
        site_has_comments = context.get('site_has_comments', UNDEFINED)
        comments = _mako_get_namespace(context, 'comments')
        posts = context.get('posts', UNDEFINED)
        index_teasers = context.get('index_teasers', UNDEFINED)
        __M_writer = context.writer()
        __M_writer('\n')
        __M_writer('\n')
        __M_writer('\n')
        if 'parent' not in context._data or not hasattr(context._data['parent'], 'content'):
            context['self'].content(**pageargs)
        

        __M_writer('\n')
        return ''
    finally:
        context.caller_stack._pop_frame()


def render_content(context,**pageargs):
    __M_caller = context.caller_stack._push_frame()
    try:
        date_format = context.get('date_format', UNDEFINED)
        helper = _mako_get_namespace(context, 'helper')
        messages = context.get('messages', UNDEFINED)
        def content():
            return render_content(context)
        site_has_comments = context.get('site_has_comments', UNDEFINED)
        comments = _mako_get_namespace(context, 'comments')
        posts = context.get('posts', UNDEFINED)
        index_teasers = context.get('index_teasers', UNDEFINED)
        __M_writer = context.writer()
        __M_writer('\n')
        for post in posts:
            __M_writer('        <div class="postdiv">\n        <a href="')
            __M_writer(str(post.permalink()))
            __M_writer('"><h2>')
            __M_writer(str(post.title()))
            __M_writer('</a></h2>\n        ')
            __M_writer(str(post.text(teaser_only=index_teasers)))
            __M_writer('\n        <p>\n        </div>\n        <div class="postmeta">\n        <small>&nbsp;§&nbsp;\n            <span class="dateline"><a href="')
            __M_writer(str(post.permalink()))
            __M_writer('" rel="bookmark"><time class="published dt-published" datetime="')
            __M_writer(str(post.date.isoformat()))
            __M_writer('" itemprop="datePublished" title="')
            __M_writer(str(messages("Publication date")))
            __M_writer('">')
            __M_writer(str(post.formatted_date(date_format)))
            __M_writer('</time></a></span>\n        </small>\n')
            if not post.meta('nocomments') and site_has_comments:
                __M_writer('             · ')
                __M_writer(str(comments.comment_link(post.permalink(), post.base_path)))
                __M_writer('\n')
            for tag in post.tags:
                __M_writer('             · ')
                __M_writer(str(tag))
                __M_writer('\n')
            __M_writer('        </div>\n        <hr>\n')
        __M_writer('    ')
        __M_writer(str(helper.html_pager()))
        __M_writer('\n    ')
        __M_writer(str(comments.comment_link_script()))
        __M_writer('\n\t')
        __M_writer(str(helper.mathjax_script(posts)))
        __M_writer('\n')
        return ''
    finally:
        context.caller_stack._pop_frame()


"""
__M_BEGIN_METADATA
{"source_encoding": "utf-8", "line_map": {"96": 20, "72": 5, "73": 6, "74": 7, "75": 8, "76": 8, "77": 8, "78": 8, "79": 9, "80": 9, "81": 14, "82": 14, "83": 14, "84": 14, "85": 14, "86": 14, "23": 3, "88": 14, "89": 16, "26": 2, "91": 17, "92": 17, "90": 17, "94": 20, "95": 20, "32": 0, "97": 22, "98": 25, "99": 25, "100": 25, "101": 26, "102": 26, "93": 19, "104": 27, "103": 27, "110": 104, "46": 2, "47": 3, "48": 4, "53": 28, "87": 14, "59": 5}, "uri": "index.tmpl", "filename": "themes/readable/templates/index.tmpl"}
__M_END_METADATA
"""
