/**
 * 往构建产物里放一个空的 .nojekyll，让 GitHub Pages 跳过 Jekyll 预处理。
 *
 * 为什么需要：GitHub Pages 从分支发布时会先用 Jekyll 过一遍，而 Jekyll 会
 * 丢掉以 _ 或 . 开头的文件和目录。现在产物里没有这种名字，但哪天出现
 * （比如给某个资源目录起名 _assets），它会在线上**静默消失** —— 本地一切
 * 正常，部署后 404，这种问题很难查。一个空文件就能让 Jekyll 整个跳过。
 *
 * 为什么用脚本而不是往 source/ 里丢一个同名文件：Hexo 不复制点开头的文件，
 * source/.nojekyll 不会出现在 public/ 里（实测确认过）。
 *
 * 【注意】这个目录是站点根的 scripts/，不是主题的 scripts/ ——
 * 主题那个是主题自带的构建脚本，这里是本站自己的，升级主题不会覆盖。
 */
'use strict'

const fs = require('fs')
const path = require('path')

hexo.extend.filter.register('after_generate', () => {
  // after_generate 触发时 public/ 还没有被创建（hexo clean 之后它是删掉的，
  // 而产物是这一步之后才写盘的）。不自己建目录的话这里会 ENOENT 直接让
  // hexo generate 失败 —— 不是静默跳过，是整个构建挂掉，已经踩过一次。
  fs.mkdirSync(hexo.public_dir, { recursive: true })
  fs.writeFileSync(path.join(hexo.public_dir, '.nojekyll'), '')
})
