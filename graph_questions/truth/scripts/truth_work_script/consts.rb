# usage: ruby consts.rb <root> files... ; JSON {file => {defs, refs:[[name, abs, nest]], reqs:[[kind, spec, rel, dyn]], autoloads:[[fq, path]]}}
require "ripper"
require "json"
root = ARGV.shift
out = {}
REQ = %w[require require_relative load require_all autoload]

def path_of(node)
  case node[0]
  when :var_ref, :var_field
    return nil unless node[1].is_a?(Array) && node[1][0] == :@const
    [[node[1][1]], false]
  when :const_ref then [[node[1][1]], false]
  when :top_const_ref, :top_const_field then [[node[1][1]], true]
  when :const_path_ref, :const_path_field
    left = path_of(node[1]); return nil unless left
    right = node[2]; return nil unless right.is_a?(Array) && right[0] == :@const
    [left[0] + [right[1]], left[1]]
  end
end

def strings_of(args)
  strs = []; rel = false; dyn = false
  stack = [args]
  until stack.empty?
    x = stack.shift
    next unless x.is_a?(Array)
    case x[0]
    when :@tstring_content then strs << x[1]
    when :string_embexpr then dyn = true
    when :@kw then rel = true if x[1] == "__FILE__"
    when :@ident then rel = true if x[1] == "__dir__"
    end
    x.each { |y| stack << y if y.is_a?(Array) }
  end
  [strs, rel, dyn]
end

def walk(node, nest, res)
  return unless node.is_a?(Array)
  case node[0]
  when :module, :class
    p = path_of(node[1])
    if p
      fq = (p[1] || nest.empty?) ? p[0].join("::") : nest.last + "::" + p[0].join("::")
      res[:defs] << fq
      walk(node[2], nest, res) if node[0] == :class && node[2]
      body = node[0] == :module ? node[2] : node[3]
      walk(body, nest + [fq], res)
      return
    end
  when :assign
    tgt = node[1]
    if tgt.is_a?(Array) && [:var_field, :const_path_field, :top_const_field].include?(tgt[0])
      p = path_of(tgt)
      if p
        fq = (p[1] || nest.empty?) ? p[0].join("::") : nest.last + "::" + p[0].join("::")
        res[:defs] << fq
        walk(node[2], nest, res)
        return
      end
    end
  when :command, :method_add_arg
    name = nil; args = nil
    if node[0] == :command && node[1].is_a?(Array) && node[1][0] == :@ident
      name = node[1][1]; args = node[2]
    elsif node[0] == :method_add_arg && node[1].is_a?(Array) && node[1][0] == :fcall && node[1][1].is_a?(Array) && node[1][1][0] == :@ident
      name = node[1][1][1]; args = node[2]
    end
    if name && REQ.include?(name) && args
      if name == "autoload"
        sym = nil; str = nil; stack = [args]
        until stack.empty?
          x = stack.pop; next unless x.is_a?(Array)
          if x[0] == :symbol_literal
            c = x.flatten.each_cons(2).find { |a, b| a == :@const }; sym = c[1] if c
          elsif x[0] == :@tstring_content then str ||= x[1]
          end
          x.each { |y| stack << y if y.is_a?(Array) }
        end
        res[:autoloads] << [(nest.empty? ? sym : nest.last + "::" + sym), str] if sym && str
      else
        strs, rel, dyn = strings_of(args)
        unless strs.empty?
          res[:reqs] << [name, (rel ? strs.join("/") : strs.join("")), rel, dyn]
        end
      end
    end
  when :var_ref, :const_path_ref, :top_const_ref
    p = path_of(node)
    if p
      res[:refs] << [p[0].join("::"), p[1], nest.dup]
      return
    end
  end
  node.each { |c| walk(c, nest, res) if c.is_a?(Array) }
end

ARGV.each do |f|
  src = File.read(File.join(root, f)) rescue next
  sexp = Ripper.sexp(src)
  next unless sexp
  res = { defs: [], refs: [], reqs: [], autoloads: [] }
  walk(sexp, [], res)
  out[f] = res
end
puts JSON.generate(out)
