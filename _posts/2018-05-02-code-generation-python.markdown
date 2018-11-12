---
layout: post
title: "Code generation with Python"
date: 2018-05-02
---
More often than not, working in a IT project requires a lot of
repetitive tasks. In particular, one area that can be very debilitating
is the creation of test data. We know it is indispensable to the
project, but it does not make that task less boring.

Let's consider this example
===========================

> You are working in a Java project. One of the thing to test is the
> validation logic of some input XML files. One object, called the
> XmlInputSuperbEnterpriseValidator (notice the Java naming convention),
> takes a XML file path as input and return true if the file is valid.

Input file is just a simple XML file, which could look like this:

``` {.xml}
<root>
  <value1>1</value1>
  <value2>a</value2>
</root>
```

where value1 accepts number between 0 and 9 and value2 accepts letters
(a-z).

To test this, one can create a test class like the following.

``` {.java}
package com.core.validator;

import static org.junit.Assert.*;

public class XmlInputSuperEnterpriseValidatorTest {

    @Test
    public void 01_normalInput_returnsTrue() {
         assertTrue(XmlInputSuperbEnterpriseValidator.validate("input/01.xml"));
    }
}
```

Then, for each test case, create the XML file and add exactly the same
test function.

When things go sideways
=======================

What if you have 50 different permutations of XML file. You'll need to
create all of them and create the exact same test methods. And what if
the specification change and you have to add new fields? Here again, a
lot of manual operation will be required to update the test cases.

What could happen here is that the tests will just be thrown away as the
maintenance is taking more effort that most people are willing to give.

As a good little software engineer, one of the question that should pop
out of your mind is: "Isn't there a better way to do that?"

Of course there is a better way
===============================

It's not rocket science, but using python (or any other language really)
to automate the test creation will save you a bunch of time and also
make everybody in the project happier.

The basic workflow is the following:

1.  Create test data definition: It could be just a simple text file
    that describes the tests you want to run.
2.  Run the script to generate the data and the test class
3.  Run the tests and enjoy

Test definition
---------------

The test definition is the input of the generator. We need to specify
what kind of test data we want to generate. In this example, we want to
generate tests that will try all possible permutations for value1 and
value2 of the input file.

The format of the test definition is up to you; here we will just use
plain text.

``` {.example}
1,2,3,4,5,6,7,8,9
a,b,c,d,e,f,g,h,i,j,k,l,m,n,o,p,q,r,s,t,u,v,w,x,y,z
```

Generating the test data and test class
---------------------------------------

### Representing our test data in Python

First things first, let's create a class that will represent the data
for one test:

``` {.python}
import os

class TestData:

    def __init__(self, name, path, value1, value2):
        self.value1 = value1
        self.value2 = value2
        self.path = path
        self.name = name

```

We have our test data representation, great. Now we need a way to
convert it to text. We could just use Python string interpolation but
there is a much better way.

### Templating language, Yokoso

A very neat way to generate text file in python is to use a templating
language. Web frameworks, such as Django or Flask, are heavy users of
templating language to generate the HTML pages from data coming from the
server.

Here, we will use [jinja2](http://jinja.pocoo.org/docs/2.10/) to
generate our XML and java files. First, define the template using jinja
templating language. Quick way is just to define it as a string in the
python file but it can also be read from file, which is better practice
when the templates are getting bigger and more numerous.

``` {.python}
XML_TEMPLATE = """<root>
    <value1>{{ test_case.value1 }}</value1>
    <value2>{{ test_case.value2 }}</value2>>
</root>
"""
```

Notice the curly brackets? Jinja will replace what's inside by whatever
objects we pass. Object should have variables 'value1' and 'value2' to
work.

The next snippet will print this template with a test case object.

``` {.python}
from jinja2 import Template

if __name__ == "__name__":
    template = Template(XML_TEMPLATE)
    test_case = TestCase('name', 'path', 'value1', 'value2')
    print(template.render(test_case=test_case)
```

We insert the test~case~ variable in the template by passing it as a
keyword argument of the render method of jinja2.Template. This will
print:

``` {.xml}
<root>
    <value1>value1</value1>
    <value2>value2</value2>>
</root>
```

Creating the template for the java test class can be done in a similar
fashion. Here, we will leverage the for loop of jinja.

``` {.python}
JAVA_TEMPLATE = """
package com.core.validator;

import static org.junit.Assert.*;

public class XmlInputSuperbEnterpriseValidatorTest {

    {% for test_case in test_cases %}
    @Test
    public void {{ test_case.name}}() {
         assertTrue(XmlInputSuperbEnterpriseValidator.validate("{{ test_case.path }}{{ test_case.name}}"));
    }
    {% endfor %}
}

"""
```

The variable to insert in the template is test~cases~. It should be an
iterable as we use it in the for loop. Here how to generate 1000 test
cases with the java class to test them.

``` {.python}
from jinja2 import Template

if __name__ == "__name__":
    java_template = Template(JAVA_TEMPLATE)
    xml_template = Template(XML_TEMPLATE)

    path_out = "/somewhere/you/want/"
    test_cases = [TestCase("{}_test".format(i),
                           path_out,
                           i,
                           i+1) for i in range(0, 1000)]
    # Create the java file
    with open(path_out + 'XmlInputSuperbEnterpriseValidatorTest.java', 'w') as f:
        f.write(java_template.render(test_cases=test_cases)

    # Create the xml files
    for test_case in test_cases:
        with open(path_out + test_case.path + test_case.name, 'w') as f:
            f.write(xml_template.render(test_case=test_case))
```

Instead of printing the rendered templates to the console, we will just
write them to a file.

### Glue everything together

We have a way to represent our tests, we have a way to print our tests
to file, we just need to have a way to read our test specification and
convert it to a TestCase object.

Our input file first line is the value1, and the second line is the
value2. To avoid cluttering the blog post, I will assume the file is
always correct and has as many elements in the first line than in the
second line.

``` {.python}
with open('test_specification') as f:
    test_input_values = [x.rstrip().split(',') for x in f.readlines()]
values1 = test_input_values[0]
values2 = test_input_values[1]
```

Then you can combine these value the way you want to create your test
cases.

Using zip:

``` {.python}
test_cases = [TestCase('{}_test'.format(nb),
                       path_out,
                       value1,
                       value2) for nb, (value1, value2) in enumerate(zip(values1, values2))]
```

zip will create a generator from many iterables. The ith element of a
zip object is a tuple containing the ith elements of each of the input
iterables. For example,

``` {.python}
for a, b in zip([1, 2], [3, 4]):
    print("{} - {}".format(a, b))
```

Will print "1 - 2" and "3 - 4".

zip is combined with enumerate. Enumerate is also very simple. It takes
an iterator. The ith element of enumerate is (i, ith element of input
iterator).

``` {.python}
for index, el in enumerate(['a','b']):
    print("Index {}: {}".format(index, el))
```

Will print "Index 0: a" and "Index 1: b". Notice that when combining zip
with enumerate, you need to add brackets when unpacking the values. Not
using brackets would throw a ValueError (not enough values to unpack
(expected 3, got 2). The reason is that enumerate is sending a tuple of
size two.

Another way to combine test cases is to use itertools.product. Product
will yield all combinaisons possible of multiple iterables.

``` {.python}
from itertools import product

for a, b in product([1, 2], ['a', 'b', 'c']):
    print("{} - {}".format(a, b))
```

will print: 1 - a 1 - b 1 - c 2 - a 2 - b 2 - c

You can use product to test all the possible combinaisons of your input
values.

``` {.python}
from itertools import product

test_cases = [TestCase('{}_test'.format(nb),
                       path_out,
                       value1,
                       value2) for nb, (value1, value2) in enumerate(product(values1, values2))]
```

There is so much to say about generators, iterators.

Generalizing this approach
==========================

In this post, we learned about how to use python and jinja2 to automate
test creation. Instead of spending your precious time writing
boilerplate code, you can just focus on what you want to test.

This is a simple example, the concept of automation is very powerful and
helps tremendously in every day life. Even if your activities do not
imply coding, there must be some repetitive task that can be automize.
For example, sending the same mail to each mail address in an excel
spreadsheet. This can be automized (see pandas to read from excel file).

If you're interested in the subject, have a look at [automate the boring
stuff with Python.](https://automatetheboringstuff.com/)
