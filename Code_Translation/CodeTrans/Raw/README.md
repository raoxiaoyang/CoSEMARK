# 数据修改声明

将 valid.java-cs.txt.cs
第 254 条数据
public override void Validate(){base.Validate();}
修改为
public virtual string resource(){return this.resource;}


将 test.java-cs.txt.cs
第 570 条数据
public System.Uri BaseUri { get; set; }
修改为
public virtual string Name(){return this.name;}

地道的方法应该修改为
public virtual string Name => this.name;

考虑实验便利，翻译成方法而非属性
且没有使用原始的 Uri