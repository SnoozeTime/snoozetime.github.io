---
layout: post
title: "Bezier curve in Unity: Bounding Boxes"
date: 2018-05-22
---
[]({{ site.url }}/assets/micromachine.jpg)

Instead of the common FPS/RPG/Platformer, for some reason I decide to
create a clone of the old micromachine, in particular the elimination
mode when players are eliminated when they are too far away from the
first player.

As the game was creating itself in my head, I stumbled against a
mathematical obstacle in the first week of prototyping. How to determine
which player is the first? How to determinate what path the AI should
follow.

It turns out that part of the answer is to represent tracks as a curve,
and Bezier curves are used in a bunch of applications from photoshop to
font creation. To find out what player is first, I would just have to
calculate the position of all pilots on the tracks.

Some reading before getting started
===================================

This article will be introducing a bit a linear algebra. In particular,
we will apply translation and rotation to our vectors. Also, we need to
find the roots of a quadratic equation. The maths are not too
complicated but feel free to read the following links beforehand:

-   [Wikipedia article on finding the roots of a quadratic
    formula](https://en.wikipedia.org/wiki/Quadratic_equation)
-   [Description of translation, rotation and their
    combinaison](http://planning.cs.uiuc.edu/node97.html)

This article builds on an existing article which can be found here:
<https://catlikecoding.com/unity/tutorials/curves-and-splines/> It shows
how to implement a Bezier curve in Unity, showing at the same time how
editor scripts work.

The last resource is an ebook called "A primer on Bezier". It can be
found [here.](https://pomax.github.io/bezierinfo/) This ebook contains
all you need to know about Bezier curves, theory and pseudocode
included.

![Initial bezier situation]({{ site.url }}/assets/bezier_initial.png)

Bounding box
============

Bounding box are useful. In my use case, I want to find the closest
point to the spline so bounding boxes will help determine what bezier
curve I should select to do the calculation!

The way to find the bounding box is to get the minimum/maximum along the
x and y axis and create the boxes from ($$x_{min}$$, $$y_{min}$$), ($$x_{min}$$,
$$y_{max}$$), ($$x_{max}$$, $$y_{min}$$), ($$x_{max}$$, $$y_{max}$$).

However, this has the tendency to create large bounding boxes so we can
get tighter boxes by aligning them along our curve. ([Part 17 - Bounding
box](https://pomax.github.io/bezierinfo/#boundingbox))

Beforehand, define the curve
----------------------------

Curve is such as

$$
B(t) = (1-t)^3P_0 + 3(1-t)^2tP_1 + 3(1-t)t^2P_2 + t^3P_3
$$

where $$P_0, P_1, P_2, P_3$$ are the control points of the curve, in
global coordinates.

Align the curve on an axis.
---------------------------

To align the curve, we first need to apply a translation T to the first
point of the curve in order to place it on the origin (0, 0). We have
$$T = -P_0$$.

``` {.csharp}
// Translation such as p0 is at (0,0)
Vector2 [] translatedVector = new Vector2[] {
    p0 - p0,
    p1 - p0,
    p2 - p0,
    p3 - p0
};
```

Then, we need to apply the rotation so that $P_3$ is on the x-axis.
Given x and y the coordinates of $P_3$, x' and y' the coordinates after
rotation $\theta$, we have the equations:

\begin{equation}
x' = xcos(theta) - ysin(theta)

y' = ycos(theta) + x sin(theta)
\end{equation}

[Don't take my word for granted
:)](https://www.siggraph.org/education/materials/HyperGraph/modeling/mod_tran/2drota.htm)

``` {.csharp}

private static Vector2 Rotate(Vector2 p, float theta) {
    // x' = x cos f - y sin f
    // y' = y cos f + x sin f
    float xp = p.x * Mathf.Cos(theta) - p.y * Mathf.Sin(theta);
    float yp = p.y * Mathf.Cos(theta) + p.x * Mathf.Sin(theta);

    return new Vector2(xp, yp);
}

```

We find theta such as $$y' = 0$$.

$$
\theta = atan(-y/x)
$$

``` {.csharp}
// Find rotation such as translatedVector[3] is on the axis
Vector2 pp3 = translatedVector[3];
float theta = Mathf.Atan(-pp3.y/pp3.x);
```

Just for fun, let's draw the Bezier curve after rotation.

``` {.csharp}

public static Vector2[] GetAlignedCurve(Vector2 p0, Vector2 p1, Vector2 p2, Vector2 p3) {

    // Translation such as p0 is at (0,0)
    Vector2 [] translatedVector = new Vector2[] {
        p0 - p0,
        p1 - p0,
        p2 - p0,
        p3 - p0
    };

    // Find rotation such as translatedVector[3] is on the axis
    Vector2 pp3 = translatedVector[3];
    float theta = Mathf.Atan(-pp3.y/pp3.x);

    // Now calculate new vectors.
    return new Vector2[] {
        Rotate(p0 - p0, theta),
        Rotate(p1 - p0, theta),
        Rotate(p2 - p0, theta),
        Rotate(p3 - p0, theta)
    };
}

```

When adding the aligned curve to the editor script, we get the
following.

![]({{ site.url}}/assets/aligned_bezier.png)

Find the bounding box for the aligned curve
-------------------------------------------

Once we have our aligned curve, we need to find its bounding box. To do
so, we need to calculate the roots of the curve for x and y in order to
get the minimum and maximum on the axis for t between 0 and 1.

To get an idea about why we want the minimum and maximum of a curve,
please refer to my amazing drawing. ![]({{ site.url }}/assets/bounding_box.png)

In this piece of art, the maximum and minimum of y are located on the
curve. For x however, only the minimum x is located on the curve. The
maximum is one of our control point. This is why we absolutely have to
include the first and last control points when we want to find the
minimum and maximum on each axis.

For a quadratic or cubic Bezier curve, it is very easy to find the
minimum and maximum for each axis. The way to do it is to calculate the
derivate of the curve, and find the t values for which this derivative
is 0. These values are called the roots of the curve for the x or y
axis. The Wikipedia article at the top of the blog article explains it
more deeply.

After deriving the Bezier equation and simplifying it a bit, we obtain:

$$
3 (-x_{p_0} + 3x_{p_1} - 3x_{p_2} + x_{p_3})t^2 + 6(x_{p_0} - 2x_{p_1} + x_{p_2})t + 3(x_{p_1} - x_{p_0}) = 0
$$

Where $x_{p_i}$ is the x coordinate of the point i. There is the same
equation for y. Now that we have reduce our equation to a simple
quadratic equation, the solution is textbook.

$$
a = 3(-x_{p_0} + 3x_{p_1} - 3x_{p_2} + x_{p_3})
$$

$$
b = 6(x_{p_0} - 2x_{p_1} + x_{p_2})
$$

$$
c = 3(x_{p_1} - x_{p_0})
$$

$$
\Delta = b^2 - 4 ac
$$

$\Delta$ (Delta) is the discriminant. We can find imaginary roots (that
cannot be represented in our 2D space) when delta is negative, so here
we are just interested about the real roots, meaning when $\Delta >= 0$.

The two roots (which can be only one is the discriminant is 0) for the
axis x are:

$$
t_1 = \frac{-b - \sqrt{\Delta}}{4ac}
$$

$$
t_2 = \frac{-b + \sqrt{\Delta}}{4ac}
$$

Notice that when $\Delta$ is 0, $t_1$ and $t_2$ are the same. For our
Bezier curve, we only care about parameter between 0 and 1 so the roots
might not be usable. In C\#, there is not much complexity. Just write
down the last equations and filter the values.

``` {.csharp}
/*
  Find the roots of a cubic bezier curve in order to find minimum and maximum
 */
private static List<float> FindRoots(Vector2 p0, Vector2 p1, Vector2 p2, Vector2 p3) {
    Vector2 a = 3 * (-p0 + 3*p1 - 3*p2 + p3);
    Vector2 b = 6 * (p0 - 2*p1 + p2);
    Vector2 c = 3 * (p1 - p0);

    List<float> roots = new List<float>();

    // along x
    float discriminantX = b.x * b.x - 4 * a.x * c.x;
    if (discriminantX < 0) {
        // No roots
    } else if (discriminantX == 0) {
        // one real root
        float rootx = (-b.x) / (2 * a.x);
        if (rootx >=0 && rootx <= 1) {
            roots.Add(rootx);
        }
    } else if (discriminantX > 0) {
        // Two real roots
        float rootx1 = (-b.x + Mathf.Sqrt(discriminantX)) / (2 * a.x);
        float rootx2 = (-b.x - Mathf.Sqrt(discriminantX)) / (2 * a.x);
        if (rootx1 >=0 && rootx1 <= 1) {
            roots.Add(rootx1);
        }
        if (rootx2 >=0 && rootx2 <= 1) {
            roots.Add(rootx2);
        }
    }

    // along y
    float discriminantY = b.y * b.y - 4 * a.y * c.y;
    if (discriminantY < 0) {
        // No roots
    } else if (discriminantY == 0) {
        // one real root
        float rooty = (-b.y) / (2 * a.y);
        if (rooty >=0 && rooty <= 1) {
            roots.Add(rooty);
        }
    } else if (discriminantY > 0) {
        // Two real roots
        float rooty1 = (-b.y + Mathf.Sqrt(discriminantY)) / (2 * a.y);
        float rooty2 = (-b.y - Mathf.Sqrt(discriminantY)) / (2 * a.y);
        if (rooty1 >=0 && rooty1 <= 1) {
            roots.Add(rooty1);
        }
        if (rooty2 >=0 && rooty2 <= 1) {
            roots.Add(rooty2);
        }
    }

    return roots;
}

```

(You can even refactor this to do the calculation once! When reading
back this code I noticed that I was a bit lazy here).

Now, our minimum and maximum along x and y would be one of the point
that has a parameter t, where t is either a root, 0 or 1.

``` {.csharp}

List<float> roots = FindRoots(pa0, pa1, pa2, pa3);


// Initialize min and max with the first point
float min_x = Mathf.Min(pa0.x, pa3.x);
float max_x = Mathf.Max(pa0.x, pa3.x);
float min_y = Mathf.Min(pa0.y, pa3.y);
float max_y = Mathf.Max(pa0.y, pa3.y);

for (int i = 0; i < roots.Count; i++) {
    float param = roots[i];
    Vector2 point = GetPoint(pa0, pa1, pa2, pa3, param);

    if (point.x > max_x) {
        max_x = point.x;
    }

    if (point.x < min_x) {
        min_x = point.x;
    }

    if (point.y > max_y) {
        max_y = point.y;
    }

    if (point.y < min_y) {
        min_y = point.y;
    }
}
```

We have our $x_min$, $x_max$, $y_min$, $y_max$. This is all we need for
drawing the bounding box.

![]({{ site.url }}/assets/bounding_box_aligned.png)

Rotate the box back
-------------------

Almost there! At this point, we have the bounding box of the aligned
curve. To get the aligned curve, we applied two transformations to our
Bezier curve: first a translation, then a rotation. To get back to the
original curve, you can simply do the inverse! First, rotate the aligned
curve by the opposite of the first rotation ($-\theta$), then translate
it by the opposite of the first translation ($-P_0$).

We can do the same with the bounding box, and it should fit our original
Bezier curve!

With the previous minima and maxima:

``` {.csharp}

return new Vector2[] {
    Rotate(new Vector2(min_x, min_y), -theta) + p0,
    Rotate(new Vector2(min_x, max_y), -theta) + p0,
    Rotate(new Vector2(max_x, min_y), -theta) + p0,
    Rotate(new Vector2(max_x, max_y), -theta) + p0,
};

```

Which gives us, at last:

![]({{ site.url }}/assets/bounding_box_final.png)

What's next?
============

All this to find the bounding boxes of each curve in our Bezier spline!
While it looks like a lot of work, these bounding boxes are really going
to help us find the projection of a point on the spline.

Instead of having to consider all the spline, now we can just reduce the
problem to a list of Bezier curves. Calculating distance to a box is
pretty simple, so we just need to find the closest boxes to our point
and for each curve, finding the closest point. This will be done by an
iterative approach (mathematical approach is out of the question here -
spoiler alert), so keep tuned for the next article.
