# Copyright 2018 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from jax import core
from .core import (lattice_join, Primitive, Primitive, Unit, unit, AbstractUnit,
                   valid_jaxtype)
from .tree_util import register_pytree_node
from typing import Any, Dict
from .util import safe_map

Array = Any

map = safe_map

jaxval_adders = {}
jaxval_adders[Unit] = lambda _, __: unit

def add_jaxvals(x, y):
  if core.get_aval(x) is core.get_aval(y) is core.abstract_unit:
    return core.unit
  else:
    return add_jaxvals_p.bind(x, y)

add_jaxvals_p = Primitive('add_any')

@add_jaxvals_p.def_impl
def add_impl(xs, ys):
  return jaxval_adders[type(xs)](xs, ys)

@add_jaxvals_p.def_abstract_eval
def add_abstract(xs, ys):
  return lattice_join(xs, ys)

jaxval_zeros_likers: Dict[type, Array] = {}

def zeros_like_aval(aval):
  return aval_zeros_likers[type(aval)](aval)

aval_zeros_likers: Dict[type, Array] = {}
aval_zeros_likers[AbstractUnit] = lambda _: unit

def zeros_like_jaxval(val):
  return zeros_like_p.bind(val)

zeros_like_p = Primitive('zeros_like')

@zeros_like_p.def_impl
def zeros_like_impl(example):
  return jaxval_zeros_likers[type(example)](example)

zeros_like_p.def_abstract_eval(lambda x: x)

class Zero(object):
  def __repr__(self):
    return "Zero"

zero = Zero()

register_pytree_node(Zero, lambda z: ((), None), lambda _, xs: zero)


def _stop_gradient_impl(x):
  if not valid_jaxtype(x):
    raise TypeError("stop_gradient only works on valid JAX arrays, but "
                    f"input argument is: {x}")
  return x

stop_gradient_p = Primitive('stop_gradient')
stop_gradient_p.def_impl(_stop_gradient_impl)
stop_gradient_p.def_abstract_eval(lambda x: x)

# the stop_gradient primitive shouldn't be staged out for XLA compilation, so we
# use a custom bind rule
@stop_gradient_p.def_custom_bind
def stop_gradient_bind(x):
  top_trace = core.find_top_trace([x])
  if top_trace is None:
    return x
  else:
    out_tracer = top_trace.process_primitive(stop_gradient_p, (x,), {})
    return core.full_lower(out_tracer)
